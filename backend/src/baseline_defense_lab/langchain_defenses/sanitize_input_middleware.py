# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B3 - input-sanitization realised as a ``before_model`` hook.

The middleware is **metadata-only**: it records the sanitisation counters
for introspection but does **not** rewrite ``bdl_document_text``. The
sanitisation that actually shapes the prompt runs PER CHANNEL inside the
shared :func:`baseline_defense_lab.toolbox.trust_separation.wrap.build_document_block`
- on the *raw* document text, exactly as the direct pipeline does.

This matters for engine parity (audit K-001): a blob-level pass here would
sanitise the document *before* the four-channel split, so an input whose
sanitisation creates or removes a surface tag (NFKC of a full-width
``[page 1]``, a zero-width split inside ``[metadata …]``) would be
classified differently than on the direct path, and the rendered prompt
would no longer be byte-identical. By leaving the document text untouched
and letting ``build_document_block`` sanitise each channel of the raw text,
both engines split the same bytes and then sanitise identically.

The always-on BiDi-control strip and the WP-5 confusables fold both live in
that per-channel ``sanitize_text`` call; the WP counters are surfaced by
:class:`WPAuditMiddleware` (also metadata-only).
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime

from ..toolbox.input_sanitizer import sanitize_text
from .state import BdlAgentState


class SanitizeInputMiddleware(AgentMiddleware):
    """Record base-sanitisation counters for ``state["bdl_document_text"]``.

    Metadata-only: runs the base ``sanitize_text`` pass (NFKC + always-on
    BiDi strip + exotic-whitespace fold + zero-width / control / Unicode-TAG
    strip + role-delimiter neutralisation + whitespace collapse) purely to
    surface the counters in ``bdl_sanitization_meta``. It does **not** rewrite
    the document text - that is sanitised per channel on the raw text inside
    ``build_document_block`` so both engines render byte-identical prompts
    (audit K-001). The WP-5 confusables counters come from
    :class:`WPAuditMiddleware`.
    """

    state_schema = BdlAgentState
    name = "bdl_sanitize_input"

    def before_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        body = state.get("bdl_document_text", "")
        # Metadata-only: compute the counters but DO NOT write the cleaned text
        # back - the per-channel sanitisation in build_document_block owns the
        # transformation, on the raw text, for parity with the direct pipeline.
        _cleaned, meta = sanitize_text(body, normalize_bidi=True, map_confusables=False)
        merged_san_meta = {**state.get("bdl_sanitization_meta", {}), **meta}
        return {"bdl_sanitization_meta": merged_san_meta}
