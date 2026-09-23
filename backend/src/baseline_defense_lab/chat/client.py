# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Minimal Ollama chat-completion client.

The client is intentionally tiny  it talks to a single Ollama endpoint
via ``/api/chat`` and returns the assistant ``content`` plus the raw
JSON for traceability. ``requests.Session`` is used for keep-alive but
no fancy retry / streaming logic is included.
"""

from __future__ import annotations

from typing import Any

import requests

from ..toolbox.reasoning import surface_response


class OllamaChatError(RuntimeError):
    """Raised when the Ollama call fails or returns a non-2xx response."""


class OllamaChatClient:
    """Tiny stateful Ollama chat client.

    Parameters
    ----------
    base_url : str
        Ollama base URL, e.g. ``http://localhost:11434``.
    timeout_seconds : int
        Per-call HTTP timeout.
    """

    def __init__(
        self, base_url: str = "http://localhost:11434", timeout_seconds: int = 480
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def list_models(self) -> list[str]:
        """Return the locally available Ollama model tags.

        Raises :class:`OllamaChatError` if the Ollama ``/api/tags`` endpoint
        cannot be reached.
        """
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaChatError(f"Failed to list Ollama tags: {exc}") from exc
        return [m["name"] for m in resp.json().get("models", [])]

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        seed: int = 0,
        num_predict: int = 700,
        temperature: float = 0.0,
        top_p: float = 1.0,
        num_ctx: int | None = None,
        think: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """Send a chat-completion request and return ``(content, raw_json)``.

        ``think`` toggles the Ollama reasoning channel (``/api/chat`` ``think``
        field). For a reasoning-capable model (e.g. qwen3)
        ``think=True`` runs an internal reasoning pass before the visible
        answer. **Caution:** a non-reasoning model (e.g. gemma3) does NOT
        ignore the flag  Ollama rejects the request with HTTP 400
        ("model does not support thinking"), which surfaces here as
        :class:`OllamaChatError`. Defaults to ``False`` so existing callers
        keep the previous fast, non-reasoning behaviour.
        """
        options: dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p,
            "seed": seed,
            "num_predict": num_predict,
        }
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": options,
        }
        try:
            resp = self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as exc:
            # Include the response body: Ollama puts the actionable error
            # there (e.g. '"gemma3:12b" does not support thinking') while
            # raise_for_status() only carries the status line. Callers key
            # graceful-degrade decisions off this text.
            body = ""
            if exc.response is not None:
                body = f"  {exc.response.text[:500]}"
            raise OllamaChatError(f"Ollama chat call failed: {exc}{body}") from exc
        except ValueError as exc:  # non-JSON 2xx body
            raise OllamaChatError(f"Ollama returned non-JSON response: {exc}") from exc
        message = raw.get("message") or {}
        content_raw = message.get("content", "") or ""
        thinking_raw = message.get("thinking") or ""
        # ``think`` is the single source of truth for whether the caller wants
        # reasoning. When ON, surface the chain-of-thought (from the channel or
        # an inline <think> block) as the merged Gedankengang/Antwort surface;
        # when OFF, strip any reasoning a thinking-by-default model (qwen3)
        # leaked into the content so the visible answer stays clean. ``truncated``
        # lets the surface helper show a note instead of raw reasoning when the
        # model was cut off mid-think before producing an answer.
        truncated = raw.get("done_reason") == "length"
        return (
            surface_response(thinking_raw, content_raw, reasoning_on=think, truncated=truncated),
            raw,
        )
