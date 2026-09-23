# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Tool 2 - Input-Sanitizer (Ingest).

NFKC + always-on BiDi strip + per-token confusables + context-aware
zero-width/format strip + role-token neutralisation + length cap
(``sanitize_text``); and the channel parser that splits the extractor blob
into BODY/METADATA/OUTLINE/ANNOTATIONS. Self-contained (no other tool depends
inward).
"""

from .channels import METADATA_KEYS, extracted_to_channels
from .sanitizer import SanitizationMetadata, sanitize_text

__all__ = [
    "METADATA_KEYS",
    "SanitizationMetadata",
    "extracted_to_channels",
    "sanitize_text",
]
