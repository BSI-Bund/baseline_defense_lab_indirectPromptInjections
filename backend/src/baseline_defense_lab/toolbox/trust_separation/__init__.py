# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Tool 1 - Trust-Separation (Prompt-Assembly).

Structural ``<untrusted_document_context>`` wrap, fresh per-request session
delimiter, caret datamarking, sandwich preamble/postamble and typed-channel
rendering. Depends on Tool 2 (``input_sanitizer``) for per-channel sanitisation
and the channel parser.
"""

from .delimiters import build_session_delimiter, escape_closing_tags
from .wrap import (
    DOCUMENT_POSTAMBLE,
    DOCUMENT_PREAMBLE,
    FULLTEXT_DATAMARK_NOTICE,
    SANDWICH_REMINDER,
    build_document_block,
    build_plain_user_turn,
    build_user_turn,
    datamark_boundaries,
    datamark_full_text,
    prepare_plain_document_text,
    resolve_session_id,
)

__all__ = [
    "DOCUMENT_POSTAMBLE",
    "DOCUMENT_PREAMBLE",
    "FULLTEXT_DATAMARK_NOTICE",
    "SANDWICH_REMINDER",
    "build_document_block",
    "build_plain_user_turn",
    "build_session_delimiter",
    "build_user_turn",
    "datamark_boundaries",
    "datamark_full_text",
    "escape_closing_tags",
    "prepare_plain_document_text",
    "resolve_session_id",
]
