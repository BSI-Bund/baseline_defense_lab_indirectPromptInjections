# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Invoke wrapper that produces the same response envelope as ``/api/chat``.

The wrapper owns the per-call timing and the final flattening of
``messages``/``model_metadata`` into the response dict that the FastAPI
endpoint serialises. Both ``/api/chat`` (direct path) and
``/api/chat_langchain`` (this path) are schema-compatible - only
``pipeline_metadata.engine`` differs.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from ..toolbox.trust_separation import resolve_session_id
from ..tools import DefenseTools
from .pipeline import LangChainPipelineHandle, build_langchain_pipeline


@dataclass(slots=True)
class LangChainChatResult:
    """Result envelope mirroring the direct path's ``/api/chat`` response."""

    messages: list[dict[str, str]]
    canary_token: str | None
    raw_text: str
    visible_text: str
    filter_metadata: dict[str, Any] | None
    tools_snapshot: dict[str, bool]
    pipeline_metadata: dict[str, Any]
    duration_ms: int
    model_metadata: dict[str, Any]
    warnings: list[str]

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dict for JSON serialisation."""
        return asdict(self)


def invoke_langchain_chat(
    *,
    tools: DefenseTools,
    model: str,
    user_question: str,
    document_text: str,
    file_name: str = "document.txt",
    history: list[dict[str, str]] | None = None,
    seed: int = 0,
    num_predict: int = 700,
    temperature: float = 0.0,
    top_p: float = 1.0,
    num_ctx: int | None = None,
    ollama_url: str | None = None,
    timeout_seconds: int = 480,
    handle: LangChainPipelineHandle | None = None,
) -> LangChainChatResult:
    """One round-trip through the LangChain-Guardrails pipeline.

    The function builds a fresh handle per call (matching the direct path's
    ``DefensePipeline(tools=...)`` per call), unless the caller pre-built one
    via :func:`build_langchain_pipeline` to amortise agent compilation across
    repeated calls with the same tool set.

    Returns a :class:`LangChainChatResult` whose field shape matches the
    ``/api/chat`` response envelope exactly. The wrapper does **no**
    sanitization, wrapping or filtering itself - all that work happens inside
    the :class:`AgentMiddleware` chain.
    """
    if handle is None:
        handle = build_langchain_pipeline(
            tools,
            model=model,
            ollama_url=ollama_url,
            seed=seed,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
            num_ctx=num_ctx,
            timeout_seconds=timeout_seconds,
        )
    mech = handle.mechanisms
    initial_state: dict[str, Any] = {
        "messages": [],
        "bdl_document_text": document_text,
        "bdl_file_name": file_name,
        "bdl_user_question": user_question,
        "bdl_history": list(history or []),
        "bdl_canary_token": handle.canary_token,
        # Internal expanded mechanism gates the middlewares read.
        "bdl_mech": mech.as_dict(),
        # Public 5-tool snapshot, echoed back as tools_snapshot.
        "bdl_tools": tools.as_dict(),
        # Resolve the session delimiter once so every middleware names the
        # identical boundary. Matches the direct pipeline, which calls
        # resolve_session_id() once in build_request.
        "bdl_session_id": resolve_session_id(mech),
        "bdl_pipeline_meta": {"engine": "langchain"},
        "bdl_filter_meta": None,
        "bdl_visible_text": None,
        "bdl_raw_text": None,
    }
    start = time.perf_counter()
    final = handle.agent.invoke(initial_state)
    duration_ms = int((time.perf_counter() - start) * 1000)
    raw_text = final.get("bdl_raw_text") or _last_ai_text(
        final.get("messages", []), reasoning_on=mech.reasoning
    )
    visible_text = final.get("bdl_visible_text") or raw_text
    pipeline_meta = dict(final.get("bdl_pipeline_meta") or {})
    pipeline_meta["engine"] = "langchain"
    return LangChainChatResult(
        messages=[_message_to_dict(m) for m in final.get("messages", [])],
        canary_token=final.get("bdl_canary_token") or handle.canary_token,
        raw_text=raw_text,
        visible_text=visible_text,
        filter_metadata=final.get("bdl_filter_meta"),
        tools_snapshot=final.get("bdl_tools") or tools.as_dict(),
        pipeline_metadata=pipeline_meta,
        duration_ms=duration_ms,
        model_metadata=final.get("bdl_model_metadata") or {},
        # Same documented footgun warning the direct path serialises - single
        # source (``DefenseTools.dependency_warnings``), engine-independent.
        warnings=tools.dependency_warnings(),
    )


def _last_ai_text(messages: list[BaseMessage], *, reasoning_on: bool) -> str:
    from ._assembly_middleware import _extract_message_text

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return _extract_message_text(msg, reasoning_on=reasoning_on)
    return ""


def _message_to_dict(msg: BaseMessage) -> dict[str, str]:
    if isinstance(msg, SystemMessage):
        role = "system"
    elif isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    else:
        role = getattr(msg, "type", "user")
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    return {"role": role, "content": content}
