# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Tool 5 - Egress-Guard (Response).

The single shared egress library (``scan_egress`` / ``filter_response``) plus
history hygiene. ``measured = shipped``:
every egress path runs this one implementation. Depends on Tool 3
(``hardened_prompt``) for the canary detector and the F1a prompt vocabulary.
"""

from .egress import (
    ALLOW_ALL_URLS,
    HIERARCHY_STRUCTURE_LEAK_THRESHOLD,
    HIERARCHY_STRUCTURE_MARKERS,
    KNOWN_INJECTION_MARKERS,
    SAFE_FILTER_RESPONSE,
    SANDWICH_REMINDER_LEAK_THRESHOLD,
    SANDWICH_REMINDER_MARKERS,
    VERBATIM_SYSTEM_PROMPT_LEAK_THRESHOLD,
    FilterResult,
    filter_response,
    scan_egress,
)
from .history import SYSTEM_PROMPT_FRAGMENT_MARKERS, filter_history

__all__ = [
    "ALLOW_ALL_URLS",
    "HIERARCHY_STRUCTURE_LEAK_THRESHOLD",
    "HIERARCHY_STRUCTURE_MARKERS",
    "KNOWN_INJECTION_MARKERS",
    "SAFE_FILTER_RESPONSE",
    "SANDWICH_REMINDER_LEAK_THRESHOLD",
    "SANDWICH_REMINDER_MARKERS",
    "SYSTEM_PROMPT_FRAGMENT_MARKERS",
    "VERBATIM_SYSTEM_PROMPT_LEAK_THRESHOLD",
    "FilterResult",
    "filter_history",
    "filter_response",
    "scan_egress",
]
