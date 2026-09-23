# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Tool 4 - Reasoning (Model-Call).

The shared think/answer merge so every engine presents the same
``=== Gedankengang === / === Antwort ===`` surface to the egress guard.
"""

from .think_merge import (
    merge_thinking_and_content,
    split_inline_thinking,
    surface_response,
)

__all__ = [
    "merge_thinking_and_content",
    "split_inline_thinking",
    "surface_response",
]
