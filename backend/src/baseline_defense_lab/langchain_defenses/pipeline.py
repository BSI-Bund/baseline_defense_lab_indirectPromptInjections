# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Compose :class:`DefenseTools` into an ``AgentMiddleware`` chain.

Public entry point: :func:`build_langchain_pipeline`. Returns a compiled
:class:`langchain.agents.create_agent` graph and the per-call canary token
(or ``None`` when the hardened-prompt tool is off).

The five public tools are folded into the internal mechanism gates
(:meth:`DefenseTools.to_mechanisms`); the middleware chain is then driven by
those gates exactly as the direct pipeline is:

==============================  ================================  ================
Mechanism gate                  Middleware                        Hook
==============================  ================================  ================
``sanitize_input``              ``SanitizeInputMiddleware``       ``before_model``
``wp5_confusables_map``         ``WPAuditMiddleware(conf=…)``     ``before_model``
``structural_wrap``             ``StructuralWrapMiddleware``      ``before_model``
``canary_token``\\
``hardened_system_prompt``\\
``structural_wrap``             ``HardenedSystemMiddleware``      ``before_model``
``sanitize_history``            ``HistorySanitizeMiddleware``     ``before_model``
``output_filter``               ``OutputFilterMiddleware``        ``after_model``
==============================  ================================  ================

Plus one private always-on ``_MessageAssemblyMiddleware`` that splices
``state["bdl_system_text"]`` + ``state["bdl_history"]`` + ``state["bdl_user_turn"]``
into the final messages list immediately before the model call. When
``structural_wrap`` is off it assembles the naive concatenation (plain
system prompt, question + raw document - no envelope, no framing).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_ollama import ChatOllama

from ..toolbox.hardened_prompt import generate_canary_token
from ..toolbox.mechanisms import DefenseMechanisms
from ..tools import DefenseTools
from ._assembly_middleware import _MessageAssemblyMiddleware
from .hardened_system_middleware import HardenedSystemMiddleware
from .history_sanitize_middleware import HistorySanitizeMiddleware
from .output_filter_middleware import OutputFilterMiddleware
from .sanitize_input_middleware import SanitizeInputMiddleware
from .state import BdlAgentState
from .structural_wrap_middleware import StructuralWrapMiddleware
from .wp_audit_middleware import WPAuditMiddleware

_LOGGER = logging.getLogger("baseline_defense_lab.langchain_defenses.pipeline")


@dataclass(frozen=True, slots=True)
class LangChainPipelineHandle:
    """Bundle of the compiled agent and the per-pipeline canary token."""

    agent: Any
    canary_token: str | None
    tools: DefenseTools
    mechanisms: DefenseMechanisms


def build_langchain_pipeline(
    tools: DefenseTools,
    *,
    model: str,
    ollama_url: str | None = None,
    seed: int = 0,
    num_predict: int = 700,
    temperature: float = 0.0,
    top_p: float = 1.0,
    num_ctx: int | None = None,
    timeout_seconds: int = 480,
) -> LangChainPipelineHandle:
    """Compile a ``create_agent`` graph for the given five-tool set.

    Parameters
    ----------
    tools : DefenseTools
        The five public defense tools.
    model : str
        Ollama tag (e.g. ``gemma3:12b``) passed verbatim to ``ChatOllama``.
    ollama_url : str, optional
        Base URL for the Ollama HTTP API. Defaults to the ``OLLAMA_URL``
        env var, then ``http://localhost:11434``.
    seed, num_predict, temperature, top_p, timeout_seconds : numeric
        Inference options threaded into ``ChatOllama``. Matches the direct
        path's keyword set so the same config can drive both engines.
    """
    base_url = ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")
    mech = tools.to_mechanisms()
    # Surface the documented footgun (hardened_prompt without egress_guard)
    # server-side, exactly as the direct DefensePipeline does, so the warning is
    # engine-independent and never silently dropped on the LangChain path.
    for warning in tools.dependency_warnings():
        _LOGGER.warning("DefenseTools dependency: %s", warning)
    canary = generate_canary_token() if mech.canary_token else None
    middleware = _build_middleware_chain(mech)
    llm_kwargs: dict[str, Any] = {
        "model": model,
        "base_url": base_url,
        "temperature": temperature,
        "top_p": top_p,
        "num_predict": num_predict,
        "seed": seed,
        "timeout": timeout_seconds,
        # The reasoning tool maps the Ollama ``think`` field through
        # ``ChatOllama``'s ``reasoning`` kwarg.
        "reasoning": mech.reasoning,
    }
    if num_ctx is not None:
        llm_kwargs["num_ctx"] = num_ctx
    llm = ChatOllama(**llm_kwargs)
    agent = create_agent(
        model=llm,
        tools=[],
        middleware=middleware,
        state_schema=BdlAgentState,
    )
    return LangChainPipelineHandle(
        agent=agent,
        canary_token=canary,
        tools=tools,
        mechanisms=mech,
    )


def _build_middleware_chain(mech: DefenseMechanisms) -> list[AgentMiddleware]:
    """Map active mechanism gates to ordered :class:`AgentMiddleware` instances.

    Order mirrors :mod:`baseline_defense_lab.toolbox.pipeline`:

    1. sanitization (basic + confusables fold)
    2. structural wrap (envelope + datamark + sandwich + session-scoped delimiter)
    3. system-prompt composition (hierarchy rule / hardened prompt / canary)
    4. history sanitization
    5. *internal* message assembly (always-on, splices into messages list)
    6. output filter (after_model)
    """
    chain: list[AgentMiddleware] = []
    if mech.sanitize_input:
        chain.append(SanitizeInputMiddleware())
    # Engine parity: on the direct path the confusables fold only applies
    # inside ``sanitize_text`` - i.e. together with ``sanitize_input``. Gate
    # it identically here so the same tool set produces the same prompt on
    # both engines.
    if mech.sanitize_input and (mech.wp1_bidi_normalize or mech.wp5_confusables_map):
        chain.append(
            WPAuditMiddleware(
                bidi=mech.wp1_bidi_normalize,
                confusables=mech.wp5_confusables_map,
            )
        )
    # The wrap exists only with the structural_wrap gate (Tool 1). The
    # fine-grained structural knobs (datamark/sandwich/session delimiter)
    # modulate the wrap and are folded from the same tool, so gating on
    # structural_wrap alone keeps both engines on the identical branch.
    if mech.structural_wrap:
        chain.append(StructuralWrapMiddleware())
    # structural_wrap is included: Tool 1 writes the instruction-hierarchy
    # rule into the system prompt in the same step it renders the wrap.
    if mech.hardened_system_prompt or mech.canary_token or mech.structural_wrap:
        chain.append(HardenedSystemMiddleware())
    if mech.sanitize_history:
        chain.append(HistorySanitizeMiddleware())
    # Always-on: turn the bdl_* state extras into the final messages list.
    chain.append(_MessageAssemblyMiddleware())
    if mech.output_filter:
        chain.append(OutputFilterMiddleware())
    return chain
