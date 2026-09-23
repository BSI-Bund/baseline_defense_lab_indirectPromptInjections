# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B6 - drop assistant turns that echo system-prompt fragments.

This is the LangChain mirror of
:func:`baseline_defense_lab.toolbox.egress_guard.history.filter_history`.
The middleware reads the conversation history out of
``state["bdl_history"]`` (a plain ``[{"role": ..., "content": ...}, ...]``
list provided by the wrapper) and writes the cleaned version back so the
assembly middleware can splice it between the system message and the
user turn.

When the ``sanitize_history`` flag is off this middleware is not added
to the chain - the assembly middleware then uses the raw history as-is.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime

from ..toolbox.egress_guard import filter_history
from .state import BdlAgentState


class HistorySanitizeMiddleware(AgentMiddleware):
    """Drop assistant turns containing characteristic system-prompt fragments."""

    state_schema = BdlAgentState
    name = "bdl_history_sanitize"

    def before_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        raw = state.get("bdl_history", [])
        cleaned = filter_history(raw)
        existing_meta = dict(state.get("bdl_pipeline_meta", {}))
        existing_meta["history_entries"] = len(cleaned)
        return {
            "bdl_history": cleaned,
            "bdl_pipeline_meta": existing_meta,
        }
