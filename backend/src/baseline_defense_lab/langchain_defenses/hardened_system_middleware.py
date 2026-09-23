# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B2 + B5 (canary) - system-prompt composition as a ``before_model`` hook.

This middleware mirrors what the direct pipeline does at
``DefensePipeline.__init__`` (canary generation) and
``DefensePipeline.build_request`` (system-prompt composition via the shared
:func:`compose_system_prompt`). It hands the resulting system text to the
assembly middleware via ``state["bdl_system_text"]`` and writes the canary
token into the state so :class:`OutputFilterMiddleware` can spot a leak.

Composition rules (single source: ``compose_system_prompt``)
-------------------------------------------------------------

* ``flags.hardened_system_prompt=True`` → the full 8-section hardened
  prompt with the per-session canary (TEIL 2 *is* the hierarchy rule -
  never duplicated).
* only ``flags.structural_wrap=True`` (Tool 1) → default prompt plus the
  instruction-hierarchy rule, written in the same step that renders the
  structural wrap.
* ``flags.canary_token=True`` alone → still generate a token and write it
  into state; the composed prompt follows the rules above.
* Without any of the three flags the middleware is **not** added to the
  chain and the assembler falls back to the default system text.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime

from ..toolbox.hardened_prompt import (
    compose_system_prompt,
    generate_canary_token,
)
from ..toolbox.mechanisms import DefenseMechanisms
from .state import BdlAgentState


class HardenedSystemMiddleware(AgentMiddleware):
    """Compose the system prompt (hardened, hierarchy-only or plain) + canary."""

    state_schema = BdlAgentState
    name = "bdl_hardened_system"

    def before_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        mech = DefenseMechanisms(**dict(state.get("bdl_mech", {})))
        canary = state.get("bdl_canary_token")
        if mech.canary_token and not canary:
            canary = generate_canary_token()
        system_text = compose_system_prompt(
            mech, canary, session_delimiter=state.get("bdl_session_id", "sec-static")
        )
        existing_meta = dict(state.get("bdl_pipeline_meta", {}))
        existing_meta["system_prompt_len"] = len(system_text)
        return {
            "bdl_canary_token": canary,
            "bdl_system_text": system_text,
            "bdl_pipeline_meta": existing_meta,
        }
