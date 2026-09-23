# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""LangChain ``AgentMiddleware``-based realisation of the five-tool defense set.

This is the **second** pipeline path of the lab. The first
(:mod:`baseline_defense_lab.toolbox`) is a plain Python composition
that talks to Ollama via :class:`OllamaChatClient`. This second path
realises the same flag set via :class:`langchain.agents.middleware.AgentMiddleware`
subclasses and the official :func:`langchain.agents.create_agent` factory.

The two paths share the exact same regex patterns, thresholds and template
literals  the LangChain middleware *imports* the helper functions from
``baseline_defense_lab.toolbox.*`` rather than re-implementing them, so both
paths stay byte-identical on the same inputs. :class:`StructuralWrapMiddleware`
is fully gated on the ``structural_wrap`` mechanism (Tool 1); without it the
internal assembly middleware renders the naive concatenation. The
instruction-hierarchy rule is injected by :class:`HardenedSystemMiddleware`
via the shared ``compose_system_prompt`` (added to the chain whenever Tool 1
or Tool 3 is active).

The package is an optional install (``pip install ".[langchain]"``) so the
core defense library stays at 3 hard dependencies.
"""

from .chat import LangChainChatResult, invoke_langchain_chat
from .hardened_system_middleware import HardenedSystemMiddleware
from .history_sanitize_middleware import HistorySanitizeMiddleware
from .output_filter_middleware import OutputFilterMiddleware
from .pipeline import build_langchain_pipeline
from .sanitize_input_middleware import SanitizeInputMiddleware
from .state import BdlAgentState
from .structural_wrap_middleware import StructuralWrapMiddleware
from .wp_audit_middleware import WPAuditMiddleware

__all__ = [
    "BdlAgentState",
    "HardenedSystemMiddleware",
    "HistorySanitizeMiddleware",
    "LangChainChatResult",
    "OutputFilterMiddleware",
    "SanitizeInputMiddleware",
    "StructuralWrapMiddleware",
    "WPAuditMiddleware",
    "build_langchain_pipeline",
    "invoke_langchain_chat",
]
