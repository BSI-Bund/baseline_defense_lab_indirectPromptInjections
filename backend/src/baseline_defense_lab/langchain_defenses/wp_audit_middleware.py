# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""WP-1 + WP-5 Unicode-hardening passes - metadata-only counters.

The two flags (``wp1_bidi_normalize``, ``wp5_confusables_map``) enable
additional Unicode-hardening passes. They live in their own middleware so
the flag → class mapping stays 1:1, and so the F1 reference numbers stay
byte-stable when only WP is toggled.

Like :class:`SanitizeInputMiddleware`, this middleware is **metadata-only**:
it runs :func:`baseline_defense_lab.toolbox.input_sanitizer.sanitizer.sanitize_text`
to obtain the WP counters but does **not** rewrite ``bdl_document_text``. The
confusables fold that actually shapes the prompt runs per channel inside
``build_document_block`` on the raw text, so both engines split identical
bytes before sanitising (audit K-001 - a blob-level pass before the channel
split would diverge from the direct path). There is **no** re-implementation
of the BiDi / confusables patterns here; the helper is the single source.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, Runtime

from ..toolbox.input_sanitizer import sanitize_text
from .state import BdlAgentState


class WPAuditMiddleware(AgentMiddleware):
    """Apply the BiDi-strip + confusables-fold passes from ``sanitize_text``.

    Parameters
    ----------
    bidi : bool
        Enable WP-1 - strip BiDi control codepoints and fold exotic whitespace.
    confusables : bool
        Enable WP-5 - map curated Cyrillic / Greek / Math confusables to
        their ASCII Latin prototypes (only for tokens that are ≥ 65 % ASCII).
    """

    state_schema = BdlAgentState
    name = "bdl_wp_audit"

    def __init__(self, *, bidi: bool = False, confusables: bool = False) -> None:
        super().__init__()
        if not (bidi or confusables):
            raise ValueError("WPAuditMiddleware must enable at least one of bidi / confusables.")
        self.bidi = bidi
        self.confusables = confusables

    def before_model(self, state: BdlAgentState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        body = state.get("bdl_document_text", "")
        # Metadata-only: compute the WP counters but DO NOT write the cleaned
        # text back (see K-001 / SanitizeInputMiddleware).
        _cleaned, meta = sanitize_text(
            body,
            normalize_bidi=self.bidi,
            map_confusables=self.confusables,
        )
        merged_san_meta = {**state.get("bdl_sanitization_meta", {})}
        if self.bidi:
            merged_san_meta["bidi_stripped"] = meta["bidi_stripped"]
        if self.confusables:
            merged_san_meta["confusables_mapped"] = meta["confusables_mapped"]
        return {"bdl_sanitization_meta": merged_san_meta}
