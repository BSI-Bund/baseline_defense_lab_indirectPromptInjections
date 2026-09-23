# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""B3 - Input sanitization.

Pipeline:

1. NFKC normalization (folds compatibility characters and most exotic
   whitespace down to ASCII).
2. **Always-on** BiDi handling (BiDi spoofing is a core
   attack primitive). Override/isolate spans (LRO/RLO/LRI/RLI/FSI … PDF/PDI)
   have their *hidden content redacted* - replaced by ``[ENTFERNT: verborgener
   Text]`` - so a concealed instruction is removed, not merely revealed; the
   remaining embedding/mark control chars (U+202A/B, U+2066–9, U+061C) and
   exotic whitespace are then stripped/folded.
3. Context-aware format-char strip: zero-width/invisible characters are
   removed, but legitimate uses survive - ZWJ inside emoji sequences and
   LRM/RLM/ALM adjacent to RTL text are preserved (blind
   stripping corrupts Arabic/Hebrew names in legitimate documents). Any other
   ``Default_Ignorable`` codepoint (CGJ, invisible math operators, Mongolian
   FVS, Hangul fillers …) has no legitimate use here and is stripped wholesale,
   so it cannot be spliced into a role delimiter or structural tag to defeat the
   literal matchers downstream.
4. Optional curated confusables map (WP-5) - gated **per token**, not per
   document, so an attacker cannot disable it with non-ASCII filler. Runs
   **after** the invisible-char strip (so zero-width fillers cannot dilute the
   per-token gate) and folds structural tokens unconditionally.
5. Role-delimiter neutralization (``<|im_start|>`` and friends become
   ``[FILTERED]``).
6. Whitespace collapsing (cap excessive newlines and run-on spaces).
7. Optional length cap (``max_chars``) with an explicit truncation
   marker.
"""

from __future__ import annotations

import re
import unicodedata

SanitizationMetadata = dict[str, int]

#: Characters that are ALWAYS stripped: ZWSP, BOM/ZWNBSP, soft hyphen,
#: word joiner, the Unicode TAG block, and Cc controls (except \t \n \r).
_UNSAFE_CHAR_PATTERN = re.compile("[​⁠﻿­\x00-\x08\x0b\x0c\x0e-\x1f\x7f\U000e0000-\U000e007f]")
#: Variation selectors VS1–16 + supplementary block. Stripped except VS16
#: directly after an emoji-range codepoint (legitimate emoji presentation).
_ROLE_DELIMITER_PATTERN = re.compile(
    r"<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>"
    r"|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|<\|eot_id\|>"
    r"|<\|start_header_id\|>|<\|end_header_id\|>",
    re.IGNORECASE,
)
_EXCESS_NEWLINES_PATTERN = re.compile(r"\n{4,}")
_EXCESS_SPACES_PATTERN = re.compile(r" {10,}")

#: BiDi control codepoints with no legitimate use in extracted PDF text:
#: embeddings/overrides (U+202A–E) and isolates (U+2066–9) - the spoofing
#: primitives. Stripped unconditionally. The *marks* LRM/RLM/ALM (incl.
#: U+061C) are handled contextually below: legitimate next to RTL text,
#: stripped elsewhere.
_BIDI_CONTROL_PATTERN = re.compile("[‪-‮⁦-⁩]")
#: Exotic whitespace codepoints mapped to ASCII space.
_EXOTIC_WHITESPACE_PATTERN = re.compile("[  -   　]")

#: Directional marks with *legitimate* RTL uses - preserved only when
#: adjacent to actual RTL text, stripped otherwise.
_DIRECTIONAL_MARKS = {"‎", "‏", "؜"}  # LRM, RLM, ALM
#: Zero-width (non-)joiners - preserved only inside emoji/complex-script
#: sequences, stripped otherwise.
_JOINERS = {"‍", "‌"}  # ZWJ, ZWNJ
_VS_RANGE = set(range(0xFE00, 0xFE10)) | set(range(0xE0100, 0xE01F0))

#: ``Default_Ignorable_Code_Point`` ranges with no legitimate use
#: in extracted document text - invisible / zero-effect codepoints an attacker
#: can splice into a structural tag or role delimiter to break a downstream
#: literal match while the model still reads the intact token. The
#: contextually-legitimate members (ZWJ/ZWNJ, LRM/RLM/ALM, variation selectors)
#: are handled *before* this catch-all in :func:`_strip_format_chars` and never
#: reach it; the ZWSP/BOM/WJ/SHY/TAG set and the BiDi controls are already gone
#: by the time it runs (``_UNSAFE_CHAR_PATTERN`` / ``_BIDI_CONTROL_PATTERN``).
#:
#: Source: derived from the Unicode Character Database, property
#: ``Default_Ignorable_Code_Point`` in ``DerivedCoreProperties.txt``
#: (https://www.unicode.org/Public/UCD/latest/ucd/DerivedCoreProperties.txt),
#: (c) 1991-2026 Unicode, Inc., under the Unicode Terms of Use
#: (SPDX ``Unicode-3.0``) - permissive and compatible with this project's
#: EUPL-1.2. The full notice is reproduced in ``THIRD-PARTY-NOTICES.md``, which
#: is where that licence expressly allows it to live. Only the ranges that
#: survive the earlier passes are listed; the property itself is larger.
_DEFAULT_IGNORABLE_RANGES: tuple[tuple[int, int], ...] = (
    (0x034F, 0x034F),  # COMBINING GRAPHEME JOINER
    (0x115F, 0x1160),  # HANGUL CHOSEONG / JUNGSEONG FILLER
    (0x17B4, 0x17B5),  # KHMER VOWEL INHERENT AQ / AA
    (0x180B, 0x180F),  # MONGOLIAN FREE VARIATION SELECTORS + VOWEL SEPARATOR
    (0x2061, 0x2064),  # FUNCTION APPLICATION .. INVISIBLE PLUS
    (0x2065, 0x2065),  # reserved (Default_Ignorable)
    (0x206A, 0x206F),  # deprecated format chars (INHIBIT SYMMETRIC SWAPPING …)
    (0x3164, 0x3164),  # HANGUL FILLER
    (0xFFA0, 0xFFA0),  # HALFWIDTH HANGUL FILLER
    (0xFFF0, 0xFFF8),  # reserved (Default_Ignorable)
    (0x1BCA0, 0x1BCA3),  # SHORTHAND FORMAT CONTROLS
    (0x1D173, 0x1D17A),  # MUSICAL SYMBOL BEGIN BEAM .. END PHRASE
    (0xE0000, 0xE0FFF),  # TAGS block + variation selectors supplement
)


def _is_default_ignorable(cp: int) -> bool:
    """Return True for an invisible ``Default_Ignorable`` codepoint to strip."""
    return any(lo <= cp <= hi for lo, hi in _DEFAULT_IGNORABLE_RANGES)


#: WP-5 - the Cyrillic/Greek/Math lookalikes of ASCII Latin identifier
#: characters that matter for this lab. Which characters are confusable is
#: informed by the Unicode UTS #39 confusables data ((c) Unicode, Inc., see
#: ``THIRD-PARTY-NOTICES.md``), but this is not a copy of ``confusables.txt``:
#: the entries here all map onto plain ASCII rather than the prototypes the
#: standard names (CYRILLIC SMALL LETTER KA becomes ``k``, not U+0138), because
#: downstream comparisons want ASCII, not the standard's equivalence classes.
#: Kept short and hardcoded so the corpus stays byte-deterministic across
#: machines.
_ASCII_CONFUSABLES_MAP: dict[str, str] = {
    # Cyrillic
    "а": "a",
    "А": "A",
    "е": "e",
    "Е": "E",
    "о": "o",
    "О": "O",
    "р": "p",
    "Р": "P",
    "с": "c",
    "С": "C",
    "х": "x",
    "Х": "X",
    "у": "y",
    "і": "i",
    "І": "I",
    "ј": "j",
    "Ј": "J",
    "к": "k",
    "К": "K",
    "м": "m",
    "М": "M",
    "ѕ": "s",
    "Ѕ": "S",
    # Greek
    "ο": "o",
    "Ο": "O",
    "α": "a",
    "Α": "A",
    "ε": "e",
    "Ε": "E",
    "ι": "i",
    "Ι": "I",
    "τ": "t",
    "Τ": "T",
    "ρ": "p",
    "Ρ": "P",
    "κ": "k",
    "Κ": "K",
    "ν": "v",
    "Ν": "N",
    "χ": "x",
    "Χ": "X",
}
_ASCII_CONFUSABLES_TABLE: dict[int, str] = {
    ord(src): dst for src, dst in _ASCII_CONFUSABLES_MAP.items()
}
#: Per-token gate: 0.65 instead of the old document-global
#: 0.7 so short mixed tokens ("Sаy" = 2/3 ASCII) are still folded while
#: genuinely non-Latin tokens (ratio ~0) stay untouched.
_CONFUSABLES_ASCII_RATIO_MIN = 0.65

#: Characters that never occur in a natural-language word - their presence marks
#: a token as *structural* (role delimiter, close tag). Such tokens bypass the
#: ASCII-ratio gate so a fully-homoglyphed ``<|ѕуѕτеm|>`` / ``</dοсumеnτ>`` is
#: still folded back to ASCII and caught by the ASCII-only role/tag matchers,
#: instead of slipping under the gate precisely because the disguise is total.
_STRUCTURAL_TOKEN_CHARS = frozenset("<>|/[]{}")

_TRUNCATION_MARKER = "[…TRUNCATED]"

#: Marker left in place of a BiDi-override / isolate span whose hidden content is
#: redacted: the camouflaged text is *removed*, not merely revealed, but an audit
#: breadcrumb stays so the analyst still sees that something was there.
_BIDI_REDACTION_MARKER = "[ENTFERNT: verborgener Text]"

#: BiDi *override* (LRO/RLO) and *isolate* (LRI/RLI/FSI) openers whose enclosed
#: span is redacted wholesale. Embeddings (LRE/RLE) are intentionally NOT here -
#: they are more often legitimate, so only their control char is stripped.
_BIDI_OVERRIDE_OPENERS = frozenset("‭‮")  # LRO, RLO
_BIDI_ISOLATE_OPENERS = frozenset("⁦⁧⁨")  # LRI, RLI, FSI
_BIDI_EMBED_OPENERS = frozenset("‪‫")  # LRE, RLE (count toward PDF nesting)
_BIDI_PDF = "‬"  # pops embedding / override
_BIDI_PDI = "⁩"  # pops isolate


def _redact_bidi_override_spans(text: str) -> tuple[str, int]:
    """Redact the *content* of BiDi override / isolate spans (not just the marks).

    An override (LRO/RLO) or isolate (LRI/RLI/FSI) is the textbook way to hide an
    instruction inside a document: the bytes are present but a human reader never
    sees them in reading order. Merely stripping the control char would leave the
    payload behind as clean, model-readable text. Instead we remove everything
    from the opener to its matching terminator (``PDF`` for overrides, ``PDI`` for
    isolates; a newline or end-of-text also terminates the scope) and leave a
    visible marker so the removal is auditable.

    Embeddings (LRE/RLE) are deliberately left to the plain control-char strip:
    they are far more often legitimate, so only their (invisible) control char is
    removed there, never the surrounding content.
    """
    if not any((c in _BIDI_OVERRIDE_OPENERS) or (c in _BIDI_ISOLATE_OPENERS) for c in text):
        return text, 0
    out: list[str] = []
    redacted = 0
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        is_isolate = c in _BIDI_ISOLATE_OPENERS
        if c in _BIDI_OVERRIDE_OPENERS or is_isolate:
            closer = _BIDI_PDI if is_isolate else _BIDI_PDF
            nested = (
                _BIDI_ISOLATE_OPENERS
                if is_isolate
                else (_BIDI_OVERRIDE_OPENERS | _BIDI_EMBED_OPENERS)
            )
            depth, j = 1, i + 1
            while j < n:
                cj = text[j]
                if cj == "\n":
                    break  # a paragraph separator terminates the BiDi scope
                if cj in nested:
                    depth += 1
                elif cj == closer:
                    depth -= 1
                    if depth == 0:
                        j += 1  # consume the matching terminator too
                        break
                j += 1
            out.append(_BIDI_REDACTION_MARKER)
            redacted += 1
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out), redacted


def _is_emoji_codepoint(char: str) -> bool:
    """Rough Extended_Pictographic approximation for joiner preservation."""
    cp = ord(char)
    return (
        0x1F000 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        or 0x2B00 <= cp <= 0x2BFF
        or cp in (0x2764, 0x2763)  # hearts - common in ZWJ sequences
    )


def _is_rtl_codepoint(char: str) -> bool:
    return unicodedata.bidirectional(char) in ("R", "AL", "AN")


def _strip_format_chars(text: str) -> tuple[str, int]:
    """Context-aware strip of joiners / directional marks / variation selectors.

    * ZWJ/ZWNJ survive only between two emoji codepoints (emoji sequences)
      or between two letters of a joining script (Arabic/Persian ZWNJ).
    * LRM/RLM/ALM survive only adjacent to genuine RTL characters.
    * Variation selectors survive only directly after an emoji codepoint
      (VS16 emoji presentation); the supplementary block is stripped.
    """
    out: list[str] = []
    removed = 0
    n = len(text)
    for i, char in enumerate(text):
        prev_c = text[i - 1] if i > 0 else ""
        next_c = text[i + 1] if i + 1 < n else ""
        if char in _JOINERS:
            emoji_seq = (
                prev_c and next_c and _is_emoji_codepoint(prev_c) and _is_emoji_codepoint(next_c)
            )
            joining_script = (
                prev_c and next_c and _is_rtl_codepoint(prev_c) and _is_rtl_codepoint(next_c)
            )
            if emoji_seq or joining_script:
                out.append(char)
            else:
                removed += 1
            continue
        if char in _DIRECTIONAL_MARKS:
            if (prev_c and _is_rtl_codepoint(prev_c)) or (next_c and _is_rtl_codepoint(next_c)):
                out.append(char)
            else:
                removed += 1
            continue
        if ord(char) in _VS_RANGE:
            if char == "️" and prev_c and _is_emoji_codepoint(prev_c):
                out.append(char)
            else:
                removed += 1
            continue
        # Catch-all for the remaining invisible Default_Ignorable codepoints
        # (CGJ, invisible math operators, Mongolian FVS, Hangul fillers …). The
        # contextual branches above already handled - and `continue`d past - the
        # members with legitimate uses, so anything reaching here is an
        # invisible splitter with no business in extracted text.
        if _is_default_ignorable(ord(char)):
            removed += 1
            continue
        out.append(char)
    return "".join(out), removed


def _map_confusables_per_token(text: str) -> tuple[str, int]:
    """Apply the confusables map per whitespace-token.

    The old document-global ≥70 %-ASCII gate could be disabled by padding
    the document with non-ASCII filler. Deciding per token makes the gate
    local: a Cyrillic-disguised ``аdmin`` inside German text is folded
    even when the document as a whole is mostly non-ASCII.
    """
    mapped_total = 0

    def _map_token(match: re.Match[str]) -> str:
        nonlocal mapped_total
        token = match.group(0)
        relevant = [c for c in token if not c.isspace()]
        if not relevant:
            return token
        ascii_chars = sum(1 for c in relevant if ord(c) < 128)
        # Structural tokens (role delimiters, close tags) contain characters no
        # natural-language word does, so the "preserve genuine non-Latin text"
        # rationale for the ratio gate does not apply - always fold them, else a
        # fully-homoglyphed "<|ѕуѕτеm|>" stays under the gate and defeats the
        # ASCII-only role/tag matchers downstream.
        structural = any(c in _STRUCTURAL_TOKEN_CHARS for c in relevant)
        if not structural and ascii_chars / len(relevant) < _CONFUSABLES_ASCII_RATIO_MIN:
            return token
        translated = token.translate(_ASCII_CONFUSABLES_TABLE)
        mapped_total += sum(1 for a, b in zip(token, translated, strict=True) if a != b)
        return translated

    result = re.sub(r"\S+", _map_token, text)
    return result, mapped_total


def sanitize_text(
    text: str,
    *,
    normalize_bidi: bool = True,
    map_confusables: bool = False,
    max_chars: int | None = None,
) -> tuple[str, SanitizationMetadata]:
    """Normalize and sanitize a piece of partially-trusted text.

    The BiDi-control strip and exotic-whitespace fold are part
    of the base pipeline (``normalize_bidi`` is kept for API stability
    and defaults to ``True``; passing ``False`` disables that handling).
    ``map_confusables`` is the
    WP-5 extension, now gated per token. ``max_chars`` caps the output
    with an explicit truncation marker.

    Returns
    -------
    tuple
        ``(sanitized_text, metadata)`` where the metadata dict is the
        per-step counter set (``removed_chars``, ``filtered_tokens``,
        ``bidi_stripped``, ``bidi_redacted_spans``, ``confusables_mapped``,
        ``truncated``).
    """
    normalized = unicodedata.normalize("NFKC", text)

    bidi_stripped = 0
    bidi_redacted = 0
    if normalize_bidi:
        # Override/isolate spans hide an instruction in plain sight - redact the
        # whole enclosed content first, then strip any remaining (embedding/mark)
        # BiDi control chars and fold exotic whitespace.
        normalized, bidi_redacted = _redact_bidi_override_spans(normalized)
        normalized, bidi_stripped = _BIDI_CONTROL_PATTERN.subn("", normalized)
        normalized = _EXOTIC_WHITESPACE_PATTERN.sub(" ", normalized)

    stripped, stripped_n = _UNSAFE_CHAR_PATTERN.subn("", normalized)
    stripped, format_n = _strip_format_chars(stripped)
    stripped_n += format_n

    # Confusables run AFTER the invisible-char strip on purpose: otherwise an
    # attacker splices zero-width fillers into a homoglyph token to push its
    # per-token ASCII ratio under the gate, the fold is skipped, and the strip
    # then quietly removes the fillers again - leaving the disguised token
    # intact. Folding here (post-strip, pre-role-filter) also lets a folded
    # ``<|іm_start|>`` reach ``_ROLE_DELIMITER_PATTERN`` as clean ASCII.
    confusables_mapped = 0
    if map_confusables:
        stripped, confusables_mapped = _map_confusables_per_token(stripped)

    filtered, filtered_n = _ROLE_DELIMITER_PATTERN.subn("[FILTERED]", stripped)

    collapsed = _EXCESS_NEWLINES_PATTERN.sub("\n\n\n", filtered)
    removed = stripped_n + (len(filtered) - len(collapsed))
    collapsed2 = _EXCESS_SPACES_PATTERN.sub(" ", collapsed)
    removed += len(collapsed) - len(collapsed2)

    truncated = 0
    if max_chars is not None and len(collapsed2) > max_chars:
        truncated = len(collapsed2) - max_chars
        collapsed2 = collapsed2[:max_chars] + _TRUNCATION_MARKER

    return collapsed2, {
        "removed_chars": removed,
        "filtered_tokens": filtered_n,
        "bidi_stripped": bidi_stripped,
        "bidi_redacted_spans": bidi_redacted,
        "confusables_mapped": confusables_mapped,
        "truncated": truncated,
    }
