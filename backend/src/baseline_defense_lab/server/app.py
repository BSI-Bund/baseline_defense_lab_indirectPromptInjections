# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""FastAPI backend for the Baseline-Defense-Lab teaching UI.

Endpoints
---------

* ``GET  /api/healthz``      - readiness probe (Ollama reachability + models).
* ``GET  /api/tools``        - the five defense tools with their descriptions.
* ``GET  /api/defaults``     - generation defaults (single source of truth).
* ``GET  /api/models``       - list of locally available Ollama models.
* ``POST /api/extract``      - extract multi-surface text from an uploaded PDF.
* ``POST /api/chat``         - full request → response pipeline for one turn
  (direct path through ``DefensePipeline`` + the native Ollama client).
* ``POST /api/chat_langchain`` - same request shape, same response schema,
  but the defenses are composed via the official
  ``langchain.agents.middleware`` API. Returns 501 without the ``[langchain]``
  optional dependency.

The static frontend is served from ``/`` (see ``frontend/``).

No authentication, loopback-only: this is a teaching stack, NOT for
production or public exposure (see README §Sicherheit).
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..chat.client import OllamaChatClient, OllamaChatError
from ..pdf_extractor import extract_pdf_text
from ..toolbox.pipeline import DefensePipeline
from ..tools import DefenseTools, tool_schema
from ._debug import configure_logging, is_debug, redact

# Optional LangChain second pipeline path. Import is guarded so a core
# install without the [langchain] extra still serves /api/chat.
try:
    from ..langchain_defenses import invoke_langchain_chat

    _LANGCHAIN_AVAILABLE = True
    _LANGCHAIN_IMPORT_ERROR: ImportError | None = None
except ImportError as exc:  # pragma: no cover - exercised on installs without the extra
    invoke_langchain_chat = None  # type: ignore[assignment]
    _LANGCHAIN_AVAILABLE = False
    _LANGCHAIN_IMPORT_ERROR = exc

_DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

_LOGGER = logging.getLogger("baseline_defense_lab.server")

#: The licence and attribution files both container images serve at the site
#: root. Named once so the routes and the SPA fallback below cannot drift apart.
_LEGAL_FILES = ("3rdpartylicenses.txt", "LICENSE", "THIRD-PARTY-NOTICES.md")

#: CORS origins. Default: the two local serving ports. Override for other
#: deployments via a comma-separated ``CORS_ORIGINS`` env var - a wildcard on
#: an unauthenticated API is a footgun.
_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]

#: Upper bound for the decoded PDF upload (bytes) - keeps a decompression
#: bomb from parking pypdf on unbounded input.
_MAX_PDF_BYTES = 25 * 1024 * 1024

#: THE single source for generation defaults. ``ChatPayload`` field defaults,
#: ``GET /api/defaults`` (consumed by the frontend on startup) and the docs all
#: derive from this dict - change it here and every layer follows.
GENERATION_DEFAULTS: dict[str, float | int] = {
    "seed": 17,  # pinned for reproducible demos (0 = no pinning)
    # Generous headroom so reasoning-by-default models (e.g. qwen3)
    # finish their internal think pass *and* a final answer before the cap.
    # num_predict is a ceiling with early stop on ``done`` - a short answer
    # still stops early, so a high cap costs nothing for non-reasoning models
    # but stops qwen3 being truncated mid-think. Not user-tunable in the UI.
    "num_predict": 4096,
    "temperature": 0.0,
    "top_p": 1.0,
}

#: Default Ollama context window. Long documents are silently truncated at the
#: model's default context size without this. Like the other generation
#: parameters it is fixed server-side and not exposed in the UI.
DEFAULT_NUM_CTX = 25_000

#: Optional comma-separated model allowlist. Empty/unset ⇒ any syntactically
#: valid Ollama tag is forwarded (demo default).
_MODEL_ALLOWLIST = frozenset(
    m.strip() for m in os.environ.get("BDL_MODEL_ALLOWLIST", "").split(",") if m.strip()
)


def _enforce_model_allowlist(model: str) -> None:
    if _MODEL_ALLOWLIST and model not in _MODEL_ALLOWLIST:
        raise HTTPException(
            status_code=400,
            detail="Modell nicht in der konfigurierten Allowlist (BDL_MODEL_ALLOWLIST).",
        )


def _is_think_unsupported_error(exc: Exception) -> bool:
    """Whether ``exc`` is a non-reasoning model rejecting the Ollama think channel.

    A model without a reasoning channel rejects ``think=true`` with HTTP 400
    ("... does not support thinking"). Matched on the word ``thinking`` alone so
    minor wording drift across Ollama versions still triggers the graceful
    fallback. Single source of truth shared by the direct (``/api/chat``) and
    LangChain (``/api/chat_langchain``) chat paths so both degrade identically.
    """
    return "thinking" in str(exc).lower()


def _default_frontend_dir() -> Path:
    """Find the static frontend directory.

    Resolution order:

    1. ``BDL_FRONTEND_DIR`` environment variable (set inside Docker).
    2. ``frontend/dist/baseline-defense-lab-frontend/browser`` (Angular CLI
       production output).
    3. ``frontend/dist/baseline-defense-lab-frontend`` (older CLI output).
    """
    env = os.environ.get("BDL_FRONTEND_DIR")
    if env:
        return Path(env)
    # app.py -> server -> baseline_defense_lab -> src -> backend -> repo root
    base = Path(__file__).resolve().parents[4] / "frontend"
    for candidate in (
        base / "dist" / "baseline-defense-lab-frontend" / "browser",
        base / "dist" / "baseline-defense-lab-frontend",
        base,
    ):
        if (candidate / "index.html").exists():
            return candidate
    return base


_FRONTEND_DIR = _default_frontend_dir()


class ChatPayload(BaseModel):
    """Request payload for ``POST /api/chat`` and ``/api/chat_langchain``."""

    model: str = Field(
        ...,
        max_length=128,
        pattern=r"^[\w.\-:/]+$",
        description="Ollama tag, e.g. 'gemma3:12b'.",
    )
    user_question: str = Field(..., max_length=8_000, description="User question / prompt.")
    document_text: str = Field(
        "",
        max_length=400_000,
        description="Untrusted document body text (capped at 400k chars).",
    )
    file_name: str = Field(
        "document.txt", max_length=255, description="Display name for the document."
    )
    tools: dict[str, bool] | None = Field(
        None,
        description=(
            "Per-tool toggles (trust_separation, input_sanitizer, "
            "hardened_prompt, reasoning, egress_guard). Omitted ⇒ all five off "
            "(unguarded baseline = naive concatenation: no "
            "<untrusted_document_context> envelope, no typed-channel split, no "
            "<user_message> framing). The full structural wrap - plus the "
            "instruction-hierarchy rule in the system prompt - arrives only "
            "with trust_separation."
        ),
    )
    history: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Prior chat turns as {'role', 'content'} dicts. Required for the "
            "egress_guard's history hygiene to have anything to filter."
        ),
    )
    seed: int = Field(
        int(GENERATION_DEFAULTS["seed"]),
        ge=0,
        description="Inference seed (0 = no pinning; default pinned for reproducibility).",
    )
    num_predict: int = Field(
        int(GENERATION_DEFAULTS["num_predict"]),
        ge=1,
        le=8192,
        description=(
            "Maximum tokens to predict. Sized to leave headroom for "
            "reasoning-capable models that spend part of the budget on the "
            "think channel before reaching the final answer."
        ),
    )
    temperature: float = Field(
        float(GENERATION_DEFAULTS["temperature"]),
        ge=0.0,
        le=2.0,
        description="Sampling temperature.",
    )
    top_p: float = Field(
        float(GENERATION_DEFAULTS["top_p"]),
        gt=0.0,
        le=1.0,
        description="Top-p sampling probability.",
    )
    num_ctx: int | None = Field(
        DEFAULT_NUM_CTX,
        ge=512,
        le=131_072,
        description=(
            "Ollama context window. Without enough headroom, long documents "
            "are silently truncated at the model's default context size."
        ),
    )


class ExtractPayload(BaseModel):
    """Request payload for ``POST /api/extract``."""

    file_name: str = Field(..., max_length=255)
    # 25 MiB decoded ≈ 34M base64 chars; the cap keeps decompression bombs and
    # runaway uploads away from pypdf.
    content_base64: str = Field(..., max_length=35_000_000)
    input_sanitizer: bool = Field(
        False,
        description=(
            "When true, apply the input-sanitizer's invisible-render drop "
            "(text render mode 3/7 or zero font size) during extraction. "
            "Default false = faithful raw upload (unguarded baseline)."
        ),
    )


def _resolve_tools(payload: ChatPayload) -> DefenseTools:
    if payload.tools is not None:
        try:
            return DefenseTools(**payload.tools)
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid tools payload: {exc}") from exc
    # Default: unguarded baseline (all five tools off).
    return DefenseTools.all_off()


def create_app(
    *,
    ollama_url: str | None = None,
    frontend_dir: Path | None = None,
) -> FastAPI:
    """Construct the FastAPI app."""
    configure_logging()
    url = ollama_url or _DEFAULT_OLLAMA_URL
    static_dir = frontend_dir or _FRONTEND_DIR

    app = FastAPI(
        title="Baseline-Defense-Lab",
        version="0.1.0",
        description="Interactive teaching lab for LLM baseline defenses against indirect prompt injection.",
        debug=is_debug(),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    client = OllamaChatClient(base_url=url, timeout_seconds=480)

    # Resolved configuration at startup (only emitted when logging is enabled
    # via BDL_DEBUG / LOG_LEVEL - no-op otherwise). No secrets in this stack.
    _LOGGER.info(
        "BDL backend config: ollama_url=%s cors_origins=%s allowlist=%s "
        "generation_defaults=%s num_ctx=%s langchain=%s",
        url,
        _CORS_ORIGINS,
        sorted(_MODEL_ALLOWLIST) or "disabled",
        GENERATION_DEFAULTS,
        DEFAULT_NUM_CTX,
        _LANGCHAIN_AVAILABLE,
    )
    if not _LANGCHAIN_AVAILABLE and _LANGCHAIN_IMPORT_ERROR is not None:
        _LOGGER.debug("LangChain import error: %r", _LANGCHAIN_IMPORT_ERROR)

    @app.get("/api/healthz")
    def healthz() -> JSONResponse:
        """Readiness probe: report Ollama reachability and available models.

        Returns HTTP 200 with ``{ollama_url, ollama_reachable: true, models}``
        when Ollama responds, or HTTP 503 with ``ollama_reachable: false`` and an
        ``error`` field when it cannot be reached.
        """
        try:
            models = client.list_models()
            return JSONResponse({"ollama_url": url, "ollama_reachable": True, "models": models})
        except OllamaChatError as exc:
            return JSONResponse(
                {
                    "ollama_url": url,
                    "ollama_reachable": False,
                    "error": str(exc),
                    "models": [],
                },
                status_code=503,
            )

    @app.get("/api/tools")
    def tools_schema() -> dict:
        """The five defense tools with their descriptions (was/warum/Grenze)."""
        return {"tools": tool_schema()}

    @app.get("/api/defaults")
    def generation_defaults() -> dict:
        """Single source for the generation defaults (consumed by the UI)."""
        return dict(GENERATION_DEFAULTS)

    @app.get("/api/models")
    def models() -> dict[str, list[str]]:
        """List the locally available Ollama model tags (HTTP 503 if unreachable)."""
        try:
            return {"models": client.list_models()}
        except OllamaChatError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/extract")
    def extract(payload: ExtractPayload) -> dict:
        """Extract multi-surface text from a base64-encoded uploaded PDF.

        Decodes ``content_base64`` (HTTP 400 on invalid base64), enforces the
        25 MiB decoded-size cap (HTTP 413), and runs the PDF text extractor
        (HTTP 422 if the bytes cannot be parsed as a PDF). Returns
        ``{file_name, text, surface_lens, bytes}``.
        """
        try:
            raw = base64.b64decode(payload.content_base64)
        except binascii.Error as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 payload.") from exc
        if len(raw) > _MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"PDF exceeds the {_MAX_PDF_BYTES // (1024 * 1024)} MiB upload limit.",
            )
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)
        try:
            text, surface_lens = extract_pdf_text(tmp_path, drop_invisible=payload.input_sanitizer)
        except Exception as exc:
            _LOGGER.warning(
                "PDF extraction failed for %r: %s", payload.file_name, exc, exc_info=is_debug()
            )
            raise HTTPException(
                status_code=422,
                detail="The uploaded file could not be parsed as a PDF.",
            ) from exc
        finally:
            tmp_path.unlink(missing_ok=True)
        return {
            "file_name": payload.file_name,
            "text": text,
            "surface_lens": surface_lens,
            "bytes": len(raw),
        }

    @app.post("/api/chat")
    def chat(payload: ChatPayload) -> dict:
        """Run one document-chat turn through the direct ``DefensePipeline``.

        Applies the requested five-tool set, calls the native Ollama client
        (with a graceful fallback when a non-reasoning model rejects the think
        channel), runs the egress guard, and returns the full introspection
        envelope (rendered messages, canary token, raw vs. visible text, filter
        metadata, tool snapshot, pipeline/model metadata, timing).
        """
        _enforce_model_allowlist(payload.model)
        tools = _resolve_tools(payload)
        pipeline = DefensePipeline(tools=tools)
        request = pipeline.build_request(
            document_text=payload.document_text,
            file_name=payload.file_name,
            user_question=payload.user_question,
            history=payload.history,
        )
        if is_debug():
            _LOGGER.debug(
                "chat request: model=%s tools=%s document=%s q_len=%d history=%d",
                payload.model,
                tools.as_dict(),
                redact(payload.document_text),
                len(payload.user_question),
                len(payload.history),
            )
        started = time.perf_counter()
        reasoning_active = tools.reasoning

        def _call(think: bool):  # type: ignore[no-untyped-def]
            return client.chat(
                model=payload.model,
                messages=request.messages,
                seed=payload.seed,
                num_predict=payload.num_predict,
                temperature=payload.temperature,
                top_p=payload.top_p,
                num_ctx=payload.num_ctx,
                think=think,
            )

        try:
            raw_text, raw_json = _call(tools.reasoning)
        except OllamaChatError as exc:
            # Graceful degrade: a non-reasoning model rejects think=true with
            # HTTP 400 ("... does not support thinking"). Retry without the
            # reasoning pass and tell the caller the defense was NOT active -
            # silent degradation would be a false sense of security. Match on
            # "thinking" alone so minor wording drift across Ollama versions
            # still triggers the fallback rather than surfacing a hard 502.
            if tools.reasoning and _is_think_unsupported_error(exc):
                _LOGGER.warning(
                    "Model %r does not support thinking; retrying without the reasoning pass.",
                    payload.model,
                    exc_info=is_debug(),
                )
                reasoning_active = False
                try:
                    raw_text, raw_json = _call(False)
                except OllamaChatError as exc2:
                    _LOGGER.error("Ollama chat call failed: %s", exc2, exc_info=is_debug())
                    raise HTTPException(
                        status_code=502,
                        detail="Ollama-Aufruf fehlgeschlagen (Details im Server-Log).",
                    ) from exc2
            else:
                _LOGGER.error("Ollama chat call failed: %s", exc, exc_info=is_debug())
                raise HTTPException(
                    status_code=502,
                    detail="Ollama-Aufruf fehlgeschlagen (Details im Server-Log).",
                ) from exc
        duration_ms = int((time.perf_counter() - started) * 1000)
        response = pipeline.process_response(raw_text)

        # ``blocked`` is a property, not a field - asdict() alone drops it and
        # the frontend's "Egress-Guard blockiert" chip never fires.
        filter_metadata = (
            {**asdict(response.filter_result), "blocked": response.filter_result.blocked}
            if response.filter_result is not None
            else None
        )
        if is_debug():
            _LOGGER.debug(
                "chat response: engine=direct duration_ms=%d reasoning_active=%s egress_blocked=%s",
                duration_ms,
                reasoning_active,
                filter_metadata["blocked"] if filter_metadata else None,
            )
        return {
            "messages": request.messages,
            "canary_token": pipeline.canary_token,
            "raw_text": raw_text,
            "visible_text": response.visible_text,
            "filter_metadata": filter_metadata,
            "tools_snapshot": tools.as_dict(),
            "warnings": tools.dependency_warnings(),
            "pipeline_metadata": {**request.metadata, "engine": "direct"},
            "duration_ms": duration_ms,
            "model_metadata": {
                "model": raw_json.get("model"),
                "eval_count": raw_json.get("eval_count"),
                "prompt_eval_count": raw_json.get("prompt_eval_count"),
                "total_duration": raw_json.get("total_duration"),
                "reasoning_active": reasoning_active,
            },
        }

    @app.post("/api/chat_langchain")
    def chat_langchain(payload: ChatPayload) -> dict:
        """Same request shape as ``/api/chat``, but composed via LangChain.

        Returns a schema-compatible response envelope so the Angular frontend
        can switch engines via a single toggle. The only guaranteed difference
        is ``pipeline_metadata.engine == "langchain"``.
        """
        if not _LANGCHAIN_AVAILABLE or invoke_langchain_chat is None:
            raise HTTPException(
                status_code=501,
                detail=(
                    "LangChain pipeline path not installed. "
                    "Install with: pip install '.[langchain]'."
                ),
            )
        _enforce_model_allowlist(payload.model)
        tools = _resolve_tools(payload)

        def _invoke(active_tools: DefenseTools):  # type: ignore[no-untyped-def]
            return invoke_langchain_chat(
                tools=active_tools,
                model=payload.model,
                user_question=payload.user_question,
                document_text=payload.document_text,
                file_name=payload.file_name,
                history=payload.history,
                seed=payload.seed,
                num_predict=payload.num_predict,
                temperature=payload.temperature,
                top_p=payload.top_p,
                num_ctx=payload.num_ctx,
                ollama_url=url,
            )

        try:
            result = _invoke(tools)
        except Exception as exc:
            # Graceful degrade mirroring the direct path: a non-reasoning model
            # rejects the think channel with HTTP 400. Rebuild the LangChain
            # pipeline without the reasoning pass - the reasoning-off mechanism
            # set makes the envelope report reasoning_active=False - instead of
            # surfacing a hard 502. Any other failure keeps the 502.
            if not (tools.reasoning and _is_think_unsupported_error(exc)):
                _LOGGER.error("LangChain chat call failed: %s", exc, exc_info=is_debug())
                raise HTTPException(
                    status_code=502,
                    detail="LangChain-Pipeline-Aufruf fehlgeschlagen (Details im Server-Log).",
                ) from exc
            _LOGGER.warning(
                "Model %r does not support thinking; retrying the LangChain "
                "pipeline without the reasoning pass.",
                payload.model,
                exc_info=is_debug(),
            )
            try:
                result = _invoke(replace(tools, reasoning=False))
            except Exception as exc2:
                _LOGGER.error("LangChain chat call failed: %s", exc2, exc_info=is_debug())
                raise HTTPException(
                    status_code=502,
                    detail="LangChain-Pipeline-Aufruf fehlgeschlagen (Details im Server-Log).",
                ) from exc2
        return {
            "messages": result.messages,
            "canary_token": result.canary_token,
            "raw_text": result.raw_text,
            "visible_text": result.visible_text,
            "filter_metadata": result.filter_metadata,
            "tools_snapshot": result.tools_snapshot,
            "warnings": result.warnings,
            "pipeline_metadata": result.pipeline_metadata,
            "duration_ms": result.duration_ms,
            "model_metadata": result.model_metadata,
        }

    # ---- static frontend --------------------------------------------------
    if static_dir.is_dir() and (static_dir / "index.html").exists():

        @app.get("/")
        def root() -> FileResponse:  # type: ignore[no-untyped-def]
            return FileResponse(static_dir / "index.html")

        # Licence and attribution files, served at the same paths the nginx
        # frontend image uses so both deployments are interchangeable. They need
        # explicit routes: the SPA fallback below answers *any* unrouted path
        # with index.html and HTTP 200, so without them a request for
        # /3rdpartylicenses.txt would look served while silently returning HTML,
        # and a compliance check that only inspects the status code would pass
        # on a missing notice. Built from ``_LEGAL_FILES`` so these routes and
        # the fallback's exemption list cannot drift apart.
        def _make_legal_route(name: str):  # type: ignore[no-untyped-def]
            def _legal_file() -> FileResponse:
                # The container images place these next to the SPA; a plain
                # local ``ng build`` does not. Answer 404 instead of raising on
                # a missing path - the route exists either way, and 404 is the
                # honest answer when the file was not deployed here.
                path = static_dir / name
                if not path.is_file():
                    raise HTTPException(status_code=404, detail=f"{name} is not deployed here")
                return FileResponse(path, media_type="text/plain; charset=utf-8")

            _legal_file.__doc__ = f"Serve {name} from the static root."
            return _legal_file

        for _legal_name in _LEGAL_FILES:
            app.get(f"/{_legal_name}", include_in_schema=False)(_make_legal_route(_legal_name))

        @app.middleware("http")
        async def _index_fallback(request: Request, call_next):  # type: ignore[no-untyped-def]
            response = await call_next(request)
            # ``/api`` keeps its own 404s, and so do the licence files above: a
            # request for a notice that was not deployed has to say 404, not
            # answer 200 with the SPA shell. A compliance check that only looks
            # at the status code would otherwise pass on a missing notice.
            if (
                response.status_code == 404
                and not request.url.path.startswith("/api")
                and request.url.path.lstrip("/") not in _LEGAL_FILES
            ):
                index = static_dir / "index.html"
                if index.exists():
                    return FileResponse(index)
            return response

        # The bundle is mounted at the ROOT, not under a prefix: ``ng build``
        # emits an ``index.html`` with ``<base href="/">`` that references
        # ``main-*.js`` and ``styles-*.css`` relative to it, so the browser asks
        # for them at the root. Under a prefix those requests fall through to the
        # SPA fallback above, which answers 200 with HTML - and the browser then
        # refuses the module scripts on strict MIME type checking, leaving the
        # page stuck on its loading notice. Registered LAST on purpose: a mount
        # at "/" matches every path, and Starlette resolves routes in
        # registration order, so ``/api/*``, ``/`` and the licence files above
        # keep precedence over it.
        app.mount("/", StaticFiles(directory=static_dir), name="static")

    return app


# uvicorn entry point: ``uvicorn baseline_defense_lab.server.app:app``
app = create_app()
