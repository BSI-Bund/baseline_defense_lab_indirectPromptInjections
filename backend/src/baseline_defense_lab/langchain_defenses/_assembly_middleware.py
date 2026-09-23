# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Internal middleware that always runs last in the input chain.

It splices the state extras (``bdl_system_text``, ``bdl_history``,
``bdl_user_turn``) into a fresh ``[system, *history, user]`` messages
list and clears any leftover messages with
``RemoveMessage(REMOVE_ALL_MESSAGES)``. It also provides V0 fall-back
behaviour: when no :class:`StructuralWrapMiddleware` ran (because the
``structural_wrap`` gate is off), it assembles the same naive
concatenation the direct pipeline uses  vanilla system prompt, then
the user question and the raw document joined into one plain user turn
(no envelope, no ``<user_message>`` framing)  so V0 reaches the model
with byte-identical input on both pipeline paths.

After the model call, the after_model hook copies ``raw_text`` /
``visible_text`` into the state for the wrapper's response envelope.
This runs *only* when :class:`OutputFilterMiddleware` did not run (i.e.
when ``flags.output_filter`` is off).

The class is prefixed with an underscore because it is not part of the
spec's flag → class mapping. It exists purely to make the spec-mandated
six classes compose cleanly into a working agent.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from ..toolbox.hardened_prompt import DEFAULT_SYSTEM_PROMPT
from ..toolbox.mechanisms import DefenseMechanisms
from ..toolbox.trust_separation import build_plain_user_turn, prepare_plain_document_text
from .state import BdlAgentState


class _MessageAssemblyMiddleware(AgentMiddleware):
    """Always-on internal middleware that finalises the messages list."""

    state_schema = BdlAgentState
    name = "bdl_internal_assembly"

    def before_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        mech = DefenseMechanisms(**dict(state.get("bdl_mech", {})))
        # ----- system message ------------------------------------------------
        system_text = state.get("bdl_system_text") or DEFAULT_SYSTEM_PROMPT
        # ----- user message --------------------------------------------------
        user_turn = state.get("bdl_user_turn")
        v0_document_block_len: int | None = None
        if not user_turn:
            # No StructuralWrapMiddleware ran (structural_wrap off). Assemble
            # the naive concatenation  question + raw document, no envelope,
            # no framing  exactly as the direct pipeline's plain branch does.
            # The input sanitizer (Tool 2) still applies inside
            # ``prepare_plain_document_text`` so its length cap + always-on
            # BiDi strip match the direct path byte-for-byte.
            user_question = state.get("bdl_user_question", "")
            doc_text = state.get("bdl_document_text", "")
            prepared = prepare_plain_document_text(doc_text, mech)
            user_turn = build_plain_user_turn(user_question, prepared)
            v0_document_block_len = len(prepared)
        # ----- history -------------------------------------------------------
        history_dicts = state.get("bdl_history", [])
        history_msgs = [_dict_to_message(d) for d in history_dicts]
        # ----- assemble ------------------------------------------------------
        final = [
            SystemMessage(content=system_text),
            *history_msgs,
            HumanMessage(content=user_turn),
        ]
        meta = dict(state.get("bdl_pipeline_meta", {}))
        meta.setdefault("system_prompt_len", len(system_text))
        # document_block_len is always present on the direct path; make sure the
        # V0 LangChain path (no StructuralWrapMiddleware) sets it too so the two
        # pipeline_metadata key sets match (audit K-005).
        if v0_document_block_len is not None:
            meta.setdefault("document_block_len", v0_document_block_len)
        meta.setdefault("user_question_len", len(state.get("bdl_user_question", "")))
        meta.setdefault("history_entries", len(history_msgs))
        return {
            "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *final],
            "bdl_pipeline_meta": meta,
        }

    def after_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        # Only fill the raw / visible / model_metadata fields when no output
        # filter has already done so. ``bdl_visible_text`` being populated is
        # the signal that ``OutputFilterMiddleware`` ran.
        if state.get("bdl_visible_text") is not None:
            return None
        messages = state.get("messages", [])
        if not messages or not isinstance(messages[-1], AIMessage):
            return None
        ai = messages[-1]
        raw_text = _extract_message_text(ai, reasoning_on=_reasoning_on(state))
        from .output_filter_middleware import _extract_model_metadata

        return {
            "bdl_raw_text": raw_text,
            "bdl_visible_text": raw_text,
            "bdl_filter_meta": None,
            "bdl_model_metadata": _extract_model_metadata(
                ai, reasoning_active=_reasoning_on(state)
            ),
        }


def _reasoning_on(state: BdlAgentState) -> bool:
    """Whether the reasoning tool was active for this call (from the gate set)."""
    return bool(dict(state.get("bdl_mech", {})).get("reasoning"))


def _extract_message_text(ai, *, reasoning_on: bool) -> str:
    """Return the visible string from an AIMessage, honouring the reasoning tool.

    ``langchain-ollama`` exposes reasoning-capable model output either via
    ``additional_kwargs['reasoning_content']`` (final answer in
    ``AIMessage.content``) or inline as ``<think>...</think>`` in the content.
    Normalisation goes through the shared
    :func:`baseline_defense_lab.toolbox.reasoning.surface_response` helper (one
    source of truth across the direct and langchain paths): with the
    reasoning tool ON the chain-of-thought is merged into the
    "=== Gedankengang / Antwort ===" surface; with it OFF any leaked
    ``<think>`` block is stripped so the visible answer stays clean.
    """
    from ..toolbox.reasoning import surface_response

    content = ai.content if isinstance(ai.content, str) else str(ai.content or "")
    extras = getattr(ai, "additional_kwargs", None) or {}
    reasoning_raw = extras.get("reasoning_content") or ""
    if not isinstance(reasoning_raw, str):
        reasoning_raw = ""
    meta = dict(getattr(ai, "response_metadata", {}) or {})
    truncated = meta.get("done_reason") == "length"
    return surface_response(reasoning_raw, content, reasoning_on=reasoning_on, truncated=truncated)


def _dict_to_message(d: dict[str, str]):
    role = d.get("role", "user")
    content = d.get("content", "")
    if role == "system":
        return SystemMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    return HumanMessage(content=content)
