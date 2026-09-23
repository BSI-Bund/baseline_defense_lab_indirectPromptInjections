# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B1 - Structural isolation via session-scoped delimiters.

The opening AND closing tag of the untrusted block carry the same
per-request session id (``<untrusted_document_context session="sec-<12hex>">``
… ``</untrusted_document_context session="sec-<12hex>">``), and the hardened
system prompt names that exact value - the model can bind both boundary ends
to an id the attacker cannot know when authoring the document. Escaping is
the primary line of defense regardless: the tags that could terminate the
wrap or impersonate a trusted channel - the close tags of the outer wrap and
the inner ``<document>`` envelope (any whitespace/attribute variant, so
forged close tags with or without a guessed id) plus ``<user_message>`` and
``<channel>`` open/close - are neutralised before assembly (see
``_FORGEABLE_TAGS``). Forged *opening* wrap/document tags and ``<system>``
tags are not escaped here; they cannot end the untrusted block and are
addressed by the hardened prompt's forged-tag rules instead.
"""

from __future__ import annotations

import re
from uuid import uuid4


def build_session_delimiter() -> str:
    """Return a fresh session identifier of the form ``sec-<12hex>``."""
    return f"sec-{uuid4().hex[:12]}"


#: Structural tags an attacker may forge inside document content to break
#: out of the wrap or impersonate a trusted channel. Tolerant patterns:
#: optional whitespace and attribute junk inside the tag (``</document >``,
#: ``</document foo="bar">``) must not dodge the escaping.
_FORGEABLE_TAGS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Close tag of the outer wrap - any whitespace/attribute variant.
    (
        re.compile(r"</\s*untrusted_document_context\b[^>]*>", re.IGNORECASE),
        "&lt;/untrusted_document_context&gt;",
    ),
    # Close tag of the inner <document> envelope - premature close.
    (
        re.compile(r"</\s*document\b[^>]*>", re.IGNORECASE),
        "&lt;/document&gt;",
    ),
    # Open/close of the user channel - tier-2 impersonation from tier-3 data.
    (
        re.compile(r"<\s*user_message\b[^>]*>", re.IGNORECASE),
        "&lt;user_message&gt;",
    ),
    (
        re.compile(r"</\s*user_message\b[^>]*>", re.IGNORECASE),
        "&lt;/user_message&gt;",
    ),
    # Typed channel sections of the four-channel wrap -
    # document data must not fake a channel boundary.
    (
        re.compile(r"<\s*channel\b[^>]*>", re.IGNORECASE),
        "&lt;channel&gt;",
    ),
    (
        re.compile(r"</\s*channel\b[^>]*>", re.IGNORECASE),
        "&lt;/channel&gt;",
    ),
)


def escape_closing_tags(text: str) -> str:
    """Neutralise structural tags an attacker could forge in document content.

    Covers the outer wrap close tag (any whitespace/attribute variant,
    including the session-scoped form), the inner ``</document>`` close
    tag, and ``<user_message>`` open/close tags - so document data can
    neither terminate the untrusted block early nor impersonate the
    user channel. The tolerant patterns already cover every
    session-scoped variant.
    """
    out = text
    for pat, replacement in _FORGEABLE_TAGS:
        out = pat.sub(replacement, out)
    return out
