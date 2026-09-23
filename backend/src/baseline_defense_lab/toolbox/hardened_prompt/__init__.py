# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Tool 3 - Hardened Prompt + Canary (System-Prompt).

The deterministic 8-section hardened system prompt and the 128-bit
encoding-aware canary it embeds. Both are leaf modules with no other tool
dependency.
"""

from .canary import CANARY_PREFIX, contains_canary, generate_canary_token
from .system_prompt import (
    DEFAULT_ASSISTANT_NAME,
    DEFAULT_CUTOFF_DATE,
    DEFAULT_PURPOSE,
    DEFAULT_SYSTEM_PROMPT,
    HARDENED_SYSTEM_PROMPT_TEMPLATE,
    INSTRUCTION_HIERARCHY_RULES,
    INSTRUCTION_HIERARCHY_SECTION,
    build_hardened_system_prompt,
    build_trust_separation_system_prompt,
    compose_system_prompt,
)

__all__ = [
    "CANARY_PREFIX",
    "DEFAULT_ASSISTANT_NAME",
    "DEFAULT_CUTOFF_DATE",
    "DEFAULT_PURPOSE",
    "DEFAULT_SYSTEM_PROMPT",
    "HARDENED_SYSTEM_PROMPT_TEMPLATE",
    "INSTRUCTION_HIERARCHY_RULES",
    "INSTRUCTION_HIERARCHY_SECTION",
    "build_hardened_system_prompt",
    "build_trust_separation_system_prompt",
    "compose_system_prompt",
    "contains_canary",
    "generate_canary_token",
]
