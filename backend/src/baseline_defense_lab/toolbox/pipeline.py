# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Pipeline - compose the active defense tools into a request/response flow.

The pipeline is intentionally a pure function on inputs (tool set, document
text, user question, raw response). It does *no* network I/O. The LLM client
lives in :mod:`baseline_defense_lab.chat.client` and calls into the pipeline
at two points:

1. Before the model call, to render the chat messages from the document plus
   the user question, with the active input-side tools applied.
2. After the model call, to run the output-side tool (egress guard) on the
   raw response.

This separation keeps the defense layer easy to exercise in isolation - no
Ollama server is needed to build a request.

The public surface is the five-tool :class:`baseline_defense_lab.tools.DefenseTools`.
Internally the pipeline folds it to a :class:`DefenseMechanisms` gate set and
hands that to the (unchanged) defense helpers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .egress_guard import FilterResult, filter_history, filter_response
from .hardened_prompt import (
    compose_system_prompt,
    generate_canary_token,
)
from .trust_separation import (
    build_document_block,
    build_plain_user_turn,
    build_user_turn,
    prepare_plain_document_text,
    resolve_session_id,
)

if TYPE_CHECKING:
    # Type-only import: the pipeline is duck-typed on the tools object (it only
    # calls ``.to_mechanisms()`` / ``.dependency_warnings()`` / ``.as_dict()``),
    # so importing DefenseTools at runtime would create a tools<->toolbox cycle.
    from ..tools import DefenseTools

_LOGGER = logging.getLogger("baseline_defense_lab.toolbox.pipeline")


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    """The composed chat-completion request after input-side defenses."""

    messages: list[dict[str, str]]
    canary_token: str | None
    tools_snapshot: dict[str, bool]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineResponse:
    """The final user-visible response after output-side defenses."""

    visible_text: str
    raw_text: str
    filter_result: FilterResult | None
    tools_snapshot: dict[str, bool]


class DefensePipeline:
    """Compose the five defense tools for one (document × tools) chat turn.

    Typical use::

        pipe = DefensePipeline(
            tools=DefenseTools(trust_separation=True, input_sanitizer=True),
        )
        request = pipe.build_request(
            document_text=...,
            file_name="lebenslauf.pdf",
            user_question="Ist der Bewerber geeignet?",
            history=[],
        )
        raw = ollama_client.chat(messages=request.messages, ...)
        response = pipe.process_response(raw)
    """

    def __init__(self, tools: DefenseTools) -> None:
        self.tools = tools
        #: Internal fine-grained gate set the defense helpers consume.
        self._mech = tools.to_mechanisms()
        for warning in tools.dependency_warnings():
            _LOGGER.warning("DefenseTools dependency: %s", warning)
        self._canary_token: str | None = (
            generate_canary_token() if self._mech.canary_token else None
        )

    # ---- request side -------------------------------------------------

    def build_request(
        self,
        *,
        document_text: str,
        file_name: str,
        user_question: str,
        history: list[dict[str, str]] | None = None,
    ) -> PipelineRequest:
        """Render the final chat messages list with input-side tools."""
        # Generate the session delimiter ONCE so the document wrap and the
        # hardened system prompt name the identical boundary.
        session_id = resolve_session_id(self._mech)
        if self._mech.structural_wrap:
            document_block = build_document_block(
                document_text=document_text,
                file_name=file_name,
                flags=self._mech,
                session_id=session_id,
            )
            user_turn = build_user_turn(
                user_question, document_block, sandwich=self._mech.sandwich_defense
            )
        else:
            # Naive concatenation - the true unguarded shape: no envelope, no
            # typed channels, no <user_message> framing, no tag escaping. Only
            # the flag-gated input sanitisation (Tool 2) still applies.
            document_block = prepare_plain_document_text(document_text, self._mech)
            user_turn = build_plain_user_turn(user_question, document_block)

        # System prompt composition (single source shared with the LangChain
        # path): hardened → full 8-section prompt; structural wrap alone →
        # default prompt + instruction-hierarchy rule; neither → default.
        system_text = compose_system_prompt(
            self._mech, self._canary_token, session_delimiter=session_id
        )

        cleaned_history = (
            filter_history(history or []) if self._mech.sanitize_history else list(history or [])
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_text}]
        messages.extend(cleaned_history)
        messages.append({"role": "user", "content": user_turn})

        return PipelineRequest(
            messages=messages,
            canary_token=self._canary_token,
            tools_snapshot=self.tools.as_dict(),
            metadata={
                "system_prompt_len": len(system_text),
                "document_block_len": len(document_block),
                "user_question_len": len(user_question),
                "history_entries": len(cleaned_history),
            },
        )

    # ---- response side ------------------------------------------------

    def process_response(self, raw_text: str) -> PipelineResponse:
        """Run the output-side tool (egress guard) on the raw model response."""
        if self._mech.output_filter:
            visible, result = filter_response(
                raw_text,
                canary=self._canary_token,
                reasoning_active=self._mech.reasoning,
            )
        else:
            visible, result = raw_text, None
        return PipelineResponse(
            visible_text=visible,
            raw_text=raw_text,
            filter_result=result,
            tools_snapshot=self.tools.as_dict(),
        )

    # ---- introspection ------------------------------------------------

    @property
    def canary_token(self) -> str | None:
        """Return the per-pipeline canary token (or ``None`` if disabled)."""
        return self._canary_token
