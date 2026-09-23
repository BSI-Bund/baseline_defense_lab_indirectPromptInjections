# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Tool 4 - Reasoning: normalise the think channel and the final answer.

Shared by every call path that toggles the Ollama reasoning channel so the
downstream egress guard always scores the identical text surface.

Three facts complicate this:

1. Ollama delivers the chain-of-thought either as a separate ``message.thinking``
   channel (when ``think=true``) **or** inline as ``<think>...</think>`` tags in
   the content. Thinking-by-default models (e.g. qwen3) emit the inline
   ``<think>`` block even when the think channel is **off** - so a request with
   the reasoning tool OFF would otherwise still show the model's reasoning.
2. ``<think>`` is only the most common convention, not the only one. Measured
   against the model zoo: ``<thought>`` (exaone-deep), ``[THINK]`` (magistral),
   ``<thinking>`` / ``<reasoning>`` (assorted fine-tunes) and the OpenAI-harmony
   channel framing (gpt-oss) all carry reasoning inline too. Recognising only
   ``<think>`` meant every other convention leaked its chain-of-thought into the
   answer even with the reasoning tool OFF.
3. The reasoning tool is the single source of truth for whether the user wants
   to see reasoning. :func:`surface_response` therefore takes ``reasoning_on``:
   OFF strips any leaked reasoning block (clean answer); ON merges the
   thinking - from either source - into the ``=== Gedankengang === / === Antwort ===``
   surface.
"""

from __future__ import annotations

import re

#: Inline chain-of-thought conventions as ``(open, close)`` pairs, matched
#: case-insensitively. Order is irrelevant - the earliest match in the text
#: wins - but the first entry is by far the most common.
_COT_DELIMITERS: tuple[tuple[str, str], ...] = (
    ("<think>", "</think>"),  # qwen3, deepseek-r1, phi4-reasoning, qwq
    ("<thinking>", "</thinking>"),
    ("<thought>", "</thought>"),  # exaone-deep
    ("<reasoning>", "</reasoning>"),
    ("[THINK]", "[/THINK]"),  # magistral
)

#: The full ``<open>...</close>`` block for every convention above.
_COT_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"{re.escape(open_)}(.*?){re.escape(close)}", re.IGNORECASE | re.DOTALL)
    for open_, close in _COT_DELIMITERS
)

#: OpenAI-harmony (gpt-oss) names its channels explicitly instead of wrapping
#: them in tags: ``<|channel|>analysis<|message|>…<|end|>`` is the reasoning,
#: ``<|channel|>final<|message|>…`` the answer.
_HARMONY_ANALYSIS = re.compile(
    r"<\|channel\|>analysis<\|message\|>(.*?)(?:<\|end\|>|<\|return\|>|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_HARMONY_FINAL = re.compile(
    r"<\|channel\|>final<\|message\|>(.*?)(?:<\|end\|>|<\|return\|>|\Z)",
    re.IGNORECASE | re.DOTALL,
)
#: Leftover harmony control tokens (``<|start|>``, ``<|end|>`` …).
_HARMONY_TOKEN = re.compile(r"<\|[a-z_]+\|>", re.IGNORECASE)

#: Shown when the reasoning tool is OFF but the model only produced (or was
#: truncated mid-) reasoning, so there is no clean answer to display.
_TRUNCATED_NOTE = (
    "(Die Ausgabe wurde durch das num_predict-Budget abgeschnitten, bevor eine "
    "vollständige Antwort vorlag - reasoning-fähige Modelle wie qwen3 verbrauchen "
    "das Budget mit internem Nachdenken, auch wenn das Reasoning-Werkzeug aus ist. "
    "Erhöhe num_predict oder wähle ein Modell ohne erzwungenes Reasoning.)"
)


def _split_harmony(content: str) -> tuple[str, str, bool] | None:
    """Split an OpenAI-harmony transcript into reasoning and answer.

    Returns ``None`` when the text is not harmony-framed, so the caller can
    fall through to the tag-based conventions. A transcript that carries only
    the ``final`` channel still counts as framed: the control tokens have to be
    stripped even though there is no chain-of-thought to hide.
    """
    analysis = _HARMONY_ANALYSIS.search(content)
    final = _HARMONY_FINAL.search(content)
    if not analysis and not final:
        return None
    thinking = analysis.group(1).strip() if analysis else ""
    answer = final.group(1) if final else content[analysis.end() :]  # type: ignore[union-attr]
    return thinking, _HARMONY_TOKEN.sub("", answer).strip(), True


def split_inline_thinking(content: str) -> tuple[str, str, bool]:
    """Pull a leaked reasoning block out of ``content``.

    Returns ``(inline_thinking, answer, had_think_marker)``. Recognises every
    convention in :data:`_COT_DELIMITERS` plus harmony channel framing, in both
    the full ``<open>...</close>`` form and the lone-closing-tag variant (some
    chat templates pre-fill the opening tag, so only the closing one reaches
    ``content``). When no thinking marker is present, returns
    ``("", content, False)`` - the content is taken as-is.
    """
    if not isinstance(content, str):
        return "", content or "", False

    harmony = _split_harmony(content)
    if harmony is not None:
        return harmony

    # A complete block pins the reasoning unambiguously; take the earliest so
    # a convention quoted *inside* another model's reasoning cannot win.
    block = min(
        (m for m in (p.search(content) for p in _COT_BLOCK_PATTERNS) if m),
        key=lambda m: m.start(),
        default=None,
    )
    if block:
        answer = content[: block.start()] + content[block.end() :]
        return block.group(1).strip(), answer.strip(), True

    lowered = content.lower()
    closers = ((lowered.find(close.lower()), close) for _, close in _COT_DELIMITERS)
    found = [(idx, close) for idx, close in closers if idx != -1]
    if found:
        idx, close = min(found)
        return content[:idx].strip(), content[idx + len(close) :].strip(), True

    return "", content, False


def surface_response(
    thinking_raw: str,
    content_raw: str,
    *,
    reasoning_on: bool,
    truncated: bool = False,
) -> str:
    """Produce the final visible text given the reasoning-tool state.

    ``reasoning_on=False`` - the user did not request reasoning, so the
    chain-of-thought is never surfaced (even for thinking-by-default models like
    qwen3, which reason inline even with ``think=false``):

    * a leaked reasoning block in any recognised convention (see
      :func:`split_inline_thinking`) is stripped, leaving the clean answer;
    * if the model only produced reasoning - no answer after the closing
      delimiter, or the response was truncated (``done_reason="length"``)
      mid-think before it - a short note is shown instead of dumping the raw
      reasoning.

    ``reasoning_on=True`` - merge the thinking (from the Ollama channel or an
    inline block) with the answer via :func:`merge_thinking_and_content`.
    """
    channel = thinking_raw.strip() if isinstance(thinking_raw, str) else ""
    inline, answer, had_think = split_inline_thinking(content_raw)
    if not reasoning_on:
        if had_think:
            return answer if answer else _TRUNCATED_NOTE
        # No thinking marker: a plain answer (non-reasoning model) - unless the
        # output was cut off mid-reasoning before any </think> was emitted.
        if truncated:
            return _TRUNCATED_NOTE
        return content_raw or ""
    thinking = channel or inline
    return merge_thinking_and_content(thinking, answer)


def merge_thinking_and_content(thinking_raw: str, content_raw: str) -> str:
    """Merge the reasoning channel and the final answer into one string.

    Shared by every call path that toggles the Ollama reasoning channel
    (the direct :class:`OllamaChatClient` and the LangChain middleware
    path), so the downstream egress guard always scores the identical
    text surface regardless of which SDK produced the response. If the
    model exhausted its ``num_predict`` budget mid-think and never wrote
    an answer, an explicit note replaces the answer so the caller knows
    to retry with a larger budget.
    """
    content_clean = content_raw.strip() if isinstance(content_raw, str) else ""
    thinking_clean = thinking_raw.strip() if isinstance(thinking_raw, str) else ""
    if thinking_clean and content_clean:
        return f"=== Gedankengang ===\n{thinking_clean}\n\n=== Antwort ===\n{content_clean}"
    if thinking_clean and not content_clean:
        return (
            "=== Gedankengang ===\n"
            f"{thinking_clean}\n\n"
            "=== Antwort ===\n"
            "(Das Modell hat sein num_predict-Budget vollständig für den "
            "Gedankengang verwendet. Erhöhe num_predict, damit auch eine "
            "finale Antwort generiert wird.)"
        )
    return content_raw
