# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Internal mechanism gates - the fine-grained knobs behind the 5 tools.

This module is **not** part of the public surface. The public interface is
:class:`baseline_defense_lab.tools.DefenseTools` (exactly five booleans).
Each tool folds one or more of these mechanism gates; the folding lives in
:meth:`baseline_defense_lab.tools.DefenseTools.to_mechanisms`.

Why keep a separate internal representation at all? The defense helpers
(:func:`document_wrap.build_document_block`, the LangChain middlewares, …)
were written against named, fine-grained gates and compose them in ways the
five-tool surface intentionally hides. Preserving the gate object keeps every
algorithm self-consistent while the API and UI expose only the five tools.

Identifier schemes (glossary - this is the single authoritative place they are
defined; audit K-010 / K-031). The module docstrings sprinkle bare ``B*`` / ``WP-*``
/ ``F1*`` tags; resolve them here:

* **T1–T5** - the five public tools (:data:`baseline_defense_lab.tools.TOOL_ORDER`):
  T1 ``trust_separation``, T2 ``input_sanitizer``, T3 ``hardened_prompt``,
  T4 ``reasoning``, T5 ``egress_guard``.
* **B1–B6** - BSI *baseline-defense categories*, **not** per-gate IDs. One
  category may span several gates and even several tools, so a bare "B3" or "B5"
  names a *category*, not a unique mechanism. Mapping (category → gate → tool):

  =========  ==========================================================  =========
  Category   Gate(s)                                                     Tool
  =========  ==========================================================  =========
  B1         ``structural_wrap`` · ``session_scoped_delimiters``         T1
  B2         ``hardened_system_prompt``                                  T3
  B3         ``sanitize_input`` [T2] · ``datamark_document_boundaries``  T2 · T1
             / ``datamark_full_text`` [T1]
  B4         ``sandwich_defense``                                        T1
  B5         ``canary_token`` [T3] · ``output_filter`` [T5]              T3 · T5
  B6         ``sanitize_history``                                        T5
  =========  ==========================================================  =========

* **WP-1 / WP-5** - Unicode work-package passes (WP-1 BiDi = deprecated no-op;
  WP-5 confusables fold), both part of T2.
* **F1a / F1c / F1d** - egress leak detectors (see
  :mod:`baseline_defense_lab.toolbox.egress_guard.egress`); there is no F1b.
* ``reasoning`` is T4 and carries no B/WP tag (it toggles the model think
  channel, not a baseline category).

Each field comment below is annotated ``<category> · T<tool>`` so a gate's tool
is always unambiguous.

The class is frozen so a request cannot mutate the gate set mid-pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DefenseMechanisms:
    """Fine-grained defense gates (internal - never serialised to the API).

    Field meanings are fixed internal gate names. They are populated
    exclusively by :meth:`DefenseTools.to_mechanisms`; callers outside the
    defense layer should never instantiate this directly.
    """

    #: B3 · T2 - NFKC + always-on BiDi strip + context-aware format-char strip +
    #: role-token neutralisation + length cap (see ``input_sanitizer.sanitizer``).
    sanitize_input: bool = False
    #: B1 · T1 - render the structural trust separation at all: the
    #: ``<untrusted_document_context>`` envelope, the typed-channel split, the
    #: forgeable-close-tag escaping, the ``<user_message>`` framing AND the
    #: instruction-hierarchy rule in the system prompt. Off ⇒ naive prompt
    #: concatenation (no wrap, no channels, no framing).
    structural_wrap: bool = False
    #: B3 · T1 - caret boundary-marking of the first/last 200 body chars.
    datamark_document_boundaries: bool = False
    #: B3 · T1 - true full-text spotlighting. Held as a code
    #: constant only; never exposed as its own UI/API switch.
    datamark_full_text: bool = False
    #: B4 · T1 - preamble + postamble around the document, reminder after the
    #: user turn.
    sandwich_defense: bool = False
    #: B5 · T3 - issue the per-request 128-bit canary embedded in the prompt.
    canary_token: bool = False
    #: B5 · T5 - run the shared egress guard on the model response.
    output_filter: bool = False
    #: B1 · T1 - fresh per-request ``sec-<12hex>`` boundary in wrap + prompt.
    session_scoped_delimiters: bool = False
    #: B2 · T3 - render the 8-section hardened system prompt.
    hardened_system_prompt: bool = False
    #: B6 · T5 - drop assistant history turns that echo system-prompt fragments.
    sanitize_history: bool = False
    #: WP-1 · T2 - deprecated; the BiDi strip is part of the base sanitizer now.
    #: Kept for signature compatibility with ``sanitize_text``; no-op.
    wp1_bidi_normalize: bool = False
    #: WP-5 · T2 - map curated Cyrillic/Greek/Math confusables to ASCII, per token.
    wp5_confusables_map: bool = False
    #: T4 - toggle the Ollama ``think`` channel before the answer (no B/WP tag).
    reasoning: bool = False

    def as_dict(self) -> dict[str, bool]:
        """Materialise the gate set as an ordered dict (internal logging)."""
        return {
            "sanitize_input": self.sanitize_input,
            "structural_wrap": self.structural_wrap,
            "datamark_document_boundaries": self.datamark_document_boundaries,
            "datamark_full_text": self.datamark_full_text,
            "sandwich_defense": self.sandwich_defense,
            "canary_token": self.canary_token,
            "output_filter": self.output_filter,
            "session_scoped_delimiters": self.session_scoped_delimiters,
            "hardened_system_prompt": self.hardened_system_prompt,
            "sanitize_history": self.sanitize_history,
            "wp1_bidi_normalize": self.wp1_bidi_normalize,
            "wp5_confusables_map": self.wp5_confusables_map,
            "reasoning": self.reasoning,
        }
