# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B5 - Canary token (per-session secret embedded in the system prompt).

A canary token is a per-session secret that the system prompt instructs
the model to never echo. If it appears in the model output, the
``output_filter`` can detect that the model has leaked privileged
context. Token format: ``CANARY-XXXXXXXX`` (hex).
"""

from __future__ import annotations

import base64
import re
from secrets import token_hex

CANARY_PREFIX = "CANARY-"
_CANARY_PATTERN = re.compile(rf"{re.escape(CANARY_PREFIX)}[0-9a-fA-F]{{8,}}")

#: Characters an attacker (or a "helpful" model) may interleave into the
#: token without changing what a human reads: whitespace and common
#: separators. Stripped before the de-obfuscated comparison.
_SEPARATOR_RE = re.compile(r"[\s\-_.:/\\|]+")


def generate_canary_token(*, hex_chars: int = 32) -> str:
    """Return a fresh canary token of the form ``CANARY-<hex>``.

    ``hex_chars=32`` (default) is 128 bits of entropy - collisions in
    model output are cryptographically implausible, so a hit is a true
    leak rather than coincidence. The floor is 8 so the generated token
    always matches the generic ``CANARY-<hex>{8,}`` detection pattern.
    """
    if hex_chars < 8:
        raise ValueError(
            "hex_chars must be >= 8 so generated tokens always match the "
            "generic CANARY-<hex>{8,} detection pattern."
        )
    return f"{CANARY_PREFIX}{token_hex(hex_chars // 2 + hex_chars % 2)[:hex_chars]}"


def contains_canary(text: str, *, canary: str | None = None) -> bool:
    """Return True iff the text leaks a canary token.

    If ``canary`` is provided, this checks for that specific session
    token - including common obfuscations a model may apply when it
    "helpfully" reformats privileged context:

    * literal substring (case-insensitive),
    * the token with interleaved whitespace/separators stripped
      (``C A N A R Y - a b …``),
    * Base64 (standard and URL-safe alphabet) of the exact token,
    * the hex encoding of the exact token bytes.

    Otherwise it falls back to the generic ``CANARY-<hex>`` pattern.
    """
    if canary is None:
        return bool(_CANARY_PATTERN.search(text))

    needle = canary.lower()
    hay = text.lower()
    if needle in hay:
        return True

    # Interleaved separators: strip them from BOTH sides and compare.
    compact_hay = _SEPARATOR_RE.sub("", hay)
    compact_needle = _SEPARATOR_RE.sub("", needle)
    if compact_needle and compact_needle in compact_hay:
        return True

    # Encoded variants of the exact token string.
    raw = canary.encode("utf-8")
    encoded_needles = (
        base64.b64encode(raw).decode("ascii").lower().rstrip("="),
        base64.urlsafe_b64encode(raw).decode("ascii").lower().rstrip("="),
        raw.hex(),
    )
    return any(enc and enc in hay for enc in encoded_needles)
