# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Custom :class:`AgentState` extension carrying the BSI-defense fields.

LangChain's default agent state only tracks the ``messages`` list. The
defense pipeline needs to thread additional per-call data through the
middleware chain - the raw document text, the file name, the user
question, the per-session canary token, the active flag set, plus a
metadata dict that each middleware can append to.

All fields are :class:`typing.NotRequired` so the state degrades
gracefully when a middleware reads a field that an upstream one did not
populate (e.g. when only :class:`OutputFilterMiddleware` is active).
"""

from __future__ import annotations

from typing import Any, NotRequired

from langchain.agents.middleware.types import AgentState


class BdlAgentState(AgentState):
    """Agent state with the per-call defense payload threaded alongside messages."""

    #: Untrusted document body - wrapped when ``structural_wrap`` (Tool 1) is
    #: on, otherwise naively appended to the question. NOT mutated by
    #: :class:`SanitizeInputMiddleware` / :class:`WPAuditMiddleware` (they are
    #: metadata-only, audit K-001); the real sanitisation happens inside the
    #: wrap / plain-turn helpers.
    bdl_document_text: NotRequired[str]
    #: Display name for the document, escaped for the ``filename=`` attribute
    #: of the structural wrap (unused on the naive path).
    bdl_file_name: NotRequired[str]
    #: User question (``<user_message>``-framed when ``structural_wrap`` is on,
    #: plain otherwise).
    bdl_user_question: NotRequired[str]
    #: Optional conversation history (list of role/content dicts).
    bdl_history: NotRequired[list[dict[str, str]]]
    #: Per-session canary token. Populated by :class:`HardenedSystemMiddleware`
    #: when the ``canary_token`` flag is on; read by :class:`OutputFilterMiddleware`.
    bdl_canary_token: NotRequired[str | None]
    #: Expanded internal mechanism-gate snapshot for the call, used by every
    #: middleware to decide whether its conditional logic kicks in. This is
    #: the 13-gate ``DefenseMechanisms.as_dict()`` - never serialised to the
    #: API; the 5-tool public snapshot rides in ``bdl_tools`` instead.
    bdl_mech: NotRequired[dict[str, bool]]
    #: Public 5-tool snapshot, echoed back in the response as ``tools_snapshot``.
    bdl_tools: NotRequired[dict[str, bool]]
    #: Session delimiter resolved ONCE per call (in :func:`invoke_langchain_chat`)
    #: so the structural wrap and the hardened system prompt name the
    #: identical boundary.
    bdl_session_id: NotRequired[str]
    #: Growing metadata dict; each middleware appends its own sub-section.
    bdl_pipeline_meta: NotRequired[dict[str, Any]]
    #: Output-filter result dict (mirrors :class:`FilterResult.__dict__`).
    bdl_filter_meta: NotRequired[dict[str, Any] | None]
    #: Final user-visible text after the output filter (or the raw text when
    #: ``output_filter`` is off). Mirrors the direct pipeline's ``visible_text``.
    bdl_visible_text: NotRequired[str | None]
    #: Raw text the model produced, before the output filter scrubs it. Mirrors
    #: the direct pipeline's ``raw_text`` field.
    bdl_raw_text: NotRequired[str | None]
    #: Pre-built system prompt (hardened, hierarchy-only or default). Populated
    #: by :class:`HardenedSystemMiddleware` via ``compose_system_prompt``.
    bdl_system_text: NotRequired[str]
    #: Pre-built ``<user_message> ... <untrusted_document_context> ...``
    #: composite. Populated by :class:`StructuralWrapMiddleware`.
    bdl_user_turn: NotRequired[str]
    #: Sanitization metadata (counters per step) emitted by
    #: :class:`SanitizeInputMiddleware` / :class:`WPAuditMiddleware`.
    bdl_sanitization_meta: NotRequired[dict[str, int]]
    #: Raw response metadata returned by the underlying ``ChatOllama`` call
    #: (model name, eval counts, total_duration). Populated by
    #: :class:`OutputFilterMiddleware` (or the assembly middleware when the
    #: filter is off) so the wrapper can echo it back in the API response.
    bdl_model_metadata: NotRequired[dict[str, Any]]
