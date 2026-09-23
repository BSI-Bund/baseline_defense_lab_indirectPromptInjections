# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B1 / B3 / B4 - structural document wrap as a ``before_model`` hook.

This middleware is the LangChain-side mirror of
:func:`baseline_defense_lab.toolbox.trust_separation.wrap.build_document_block`
plus the sandwich-reminder append at the end of the user turn. It does
**not** re-implement any wrap logic; it imports the helper functions
from ``toolbox.trust_separation`` and forwards the active flags.

The middleware is added to the chain only when the ``structural_wrap``
gate (Tool 1, ``trust_separation``) is on - the wrap exists exclusively
with that tool. With the gate off the internal assembly middleware
(``_MessageAssemblyMiddleware``) assembles the naive concatenation
instead (no envelope, no framing), exactly as the direct pipeline does.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime

from ..toolbox.mechanisms import DefenseMechanisms
from ..toolbox.trust_separation import build_document_block, build_user_turn
from .state import BdlAgentState


class StructuralWrapMiddleware(AgentMiddleware):
    """Pre-compute ``bdl_user_turn`` from the structural-wrap flags.

    The assembly middleware later splices this into the final messages
    list. By pre-computing here we keep the spec's flag → class mapping
    explicit: each flag turns a specific knob on the
    :func:`build_document_block` call.
    """

    state_schema = BdlAgentState
    name = "bdl_structural_wrap"

    def before_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        mech = DefenseMechanisms(**dict(state.get("bdl_mech", {})))
        doc_text = state.get("bdl_document_text", "")
        file_name = state.get("bdl_file_name", "document.txt")
        user_question = state.get("bdl_user_question", "")
        # ``build_document_block`` performs the REAL sanitisation per channel on
        # the raw document text - the same call the direct pipeline makes - and
        # that is also where the per-channel length caps (body 200k / aux 2k)
        # and the always-on BiDi strip live. The SanitizeInput / WPAudit
        # middlewares that ran earlier are metadata-only and do NOT mutate
        # ``bdl_document_text`` (audit K-001), so ``doc_text`` here is the raw
        # text and the channel split matches the direct path byte-for-byte.
        wrap_mech = DefenseMechanisms(
            sanitize_input=mech.sanitize_input,
            wp1_bidi_normalize=mech.wp1_bidi_normalize,
            wp5_confusables_map=mech.wp5_confusables_map,
            structural_wrap=mech.structural_wrap,
            # datamark_full_text is a code constant on the direct path; thread the
            # current value through instead of dropping it, so the two engines
            # never silently diverge if it is ever enabled (audit K-039).
            datamark_full_text=mech.datamark_full_text,
            datamark_document_boundaries=mech.datamark_document_boundaries,
            sandwich_defense=mech.sandwich_defense,
            session_scoped_delimiters=mech.session_scoped_delimiters,
        )
        document_block = build_document_block(
            document_text=doc_text,
            file_name=file_name,
            flags=wrap_mech,
            session_id=state.get("bdl_session_id"),
        )
        user_turn = build_user_turn(user_question, document_block, sandwich=mech.sandwich_defense)
        # Flat pipeline-metadata only (Record<string, str|number>): never nest a
        # dict here - the frontend type and the schema-equality claim depend on
        # it (audit K-005).
        existing_meta = dict(state.get("bdl_pipeline_meta", {}))
        existing_meta["document_block_len"] = len(document_block)
        existing_meta["user_question_len"] = len(user_question)
        return {
            "bdl_user_turn": user_turn,
            "bdl_pipeline_meta": existing_meta,
        }
