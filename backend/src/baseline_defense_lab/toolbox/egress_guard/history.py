# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B6 - History sanitization.

Drops any past assistant turn that contains characteristic system-prompt
fragments. This prevents a previously-leaked context from being re-fed
into the model on a follow-up turn ("memory poisoning").
"""

from __future__ import annotations

from collections.abc import Iterable

#: Fragments that should never appear verbatim in a user-facing assistant
#: turn - the strongest signal that a previous turn leaked privileged context.
#:
#: These are characteristic phrases of the CURRENT system-prompt variants
#: (``hardened_prompt.system_prompt``: the full hardened template AND the
#: trust_separation-only composition), the wrap boundary (rendered when the
#: ``trust_separation`` tool is on) and the canary prefix. They MUST stay in
#: sync with the templates: the section headers and the "hoechste Autoritaet"
#: phrasing were previously stale (they named an earlier template), which
#: silently disarmed the egress fragment detector (audit K-002). When a
#: template changes, update these markers in the same change.
#:
#: The hierarchy rule is covered by its two concrete HEADERS (one per prompt
#: variant), never by the bare term "INSTRUKTIONS-HIERARCHIE": ``filter_history``
#: drops a turn on a single hit, and the bare term is ordinary vocabulary in
#: this lab (the tool descriptions - and compliant model answers that flag an
#: override attempt per TEIL 8 - legitimately use it).
SYSTEM_PROMPT_FRAGMENT_MARKERS: tuple[str, ...] = (
    "TEIL 1: IDENTITAET",
    "TEIL 2: INSTRUKTIONS-HIERARCHIE",
    "=== INSTRUKTIONS-HIERARCHIE ===",
    "TEIL 3: DATEN-/INSTRUKTIONS-TRENNUNG",
    "CANARY / GEHEIMNIS",
    "hoechste Autoritaet",
    "untrusted_document_context",
    "CANARY-",
)


def _contains_fragment(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in SYSTEM_PROMPT_FRAGMENT_MARKERS)


def filter_history(
    messages: Iterable[dict[str, str]],
) -> list[dict[str, str]]:
    """Drop any assistant turn that looks like it leaked privileged content.

    The function keeps system / user / tool turns unchanged and only
    inspects ``role == "assistant"`` entries. A dropped turn is replaced
    by a short refusal marker so the conversation flow stays consistent
    for the model.
    """
    out: list[dict[str, str]] = []
    for msg in messages:
        if msg.get("role") != "assistant":
            out.append(msg)
            continue
        content = msg.get("content", "")
        if _contains_fragment(content):
            out.append(
                {
                    "role": "assistant",
                    "content": "[Vorherige Antwort entfernt: enthielt Systemkontext.]",
                }
            )
        else:
            out.append(msg)
    return out
