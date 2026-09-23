# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B5 - output filter as an ``after_model`` hook.

Wraps :func:`baseline_defense_lab.toolbox.egress_guard.egress.filter_response`.
The middleware reads the last AI message off the state, runs the F1a /
F1c / F1d / canary / injection-marker / URL-exfiltration checks and stores
the raw text, the filtered visible text and the structured FilterResult
dict into the agent state for the response envelope.

It does **not** mutate the AIMessage in the graph state: the raw model
output is deliberately preserved in the introspection envelope
(``raw_text``) alongside the filtered ``visible_text`` - this is a teaching
stack, and both fields ship on both engines by design. Consumers read
``visible_text`` for the safe answer; ``raw_text`` shows what the model
actually produced (audit K-004).

The middleware is only added to the chain when ``flags.output_filter``
is on; otherwise the assembly middleware fills ``bdl_raw_text`` /
``bdl_visible_text`` from the raw AI message directly.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime
from langchain_core.messages import AIMessage

from ..toolbox.egress_guard import filter_response
from .state import BdlAgentState


class OutputFilterMiddleware(AgentMiddleware):
    """Run :func:`filter_response` on the model's reply and stash the result."""

    state_schema = BdlAgentState
    name = "bdl_output_filter"

    def after_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages or not isinstance(messages[-1], AIMessage):
            return None
        ai = messages[-1]
        from ._assembly_middleware import _extract_message_text, _reasoning_on

        reasoning_on = _reasoning_on(state)
        raw_text = _extract_message_text(ai, reasoning_on=reasoning_on)
        canary = state.get("bdl_canary_token")
        visible_text, result = filter_response(
            raw_text, canary=canary, reasoning_active=reasoning_on
        )
        # Preserve the model_metadata that the assembly middleware will pluck
        # out for the wrapper's response envelope.
        model_metadata = _extract_model_metadata(ai, reasoning_active=reasoning_on)
        return {
            "bdl_raw_text": raw_text,
            "bdl_visible_text": visible_text,
            # ``blocked`` is a property - include it explicitly (parity with
            # the direct path; asdict() drops properties).
            "bdl_filter_meta": {**asdict(result), "blocked": result.blocked},
            "bdl_model_metadata": model_metadata,
        }


def _extract_model_metadata(message: AIMessage, *, reasoning_active: bool) -> dict[str, Any]:
    """Pluck the model_metadata fields the direct path returns.

    Mirrors the direct path's ``model_metadata`` (four raw-Ollama fields plus
    ``reasoning_active``). ``reasoning_active`` carries the same semantics as
    the direct path (``/api/chat``): the reasoning tool was requested and not
    rejected - the caller passes the reasoning-off gate on the think-fallback.
    """
    meta = dict(getattr(message, "response_metadata", {}) or {})
    usage = dict(getattr(message, "usage_metadata", {}) or {})
    return {
        "model": meta.get("model") or meta.get("model_name"),
        "eval_count": meta.get("eval_count") or usage.get("output_tokens"),
        "prompt_eval_count": meta.get("prompt_eval_count") or usage.get("input_tokens"),
        "total_duration": meta.get("total_duration"),
        "reasoning_active": reasoning_active,
    }
