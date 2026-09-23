# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Multi-surface PDF text extraction.

Extracts the union of:

* Page text streams (the body the user sees). With ``drop_invisible`` set
  (the ``input_sanitizer`` defense), invisibly-rendered runs (text render
  mode 3/7 or a zero font size) are dropped so text a human never sees in the
  PDF cannot be smuggled into the prompt; the plain upload path keeps them
  (faithful extraction, so the unguarded baseline still exposes the payload).
* ``/Title``, ``/Subject``, ``/Keywords``, ``/Creator`` from PDF metadata.
* Annotations (``/Contents`` of any ``/Annot`` object on each page).
* Outline / bookmark titles.

Each surface contributes a separate text chunk in the returned blob,
prefixed with a tag for traceability. The implementation uses ``pypdf``
only  no native binaries required.
"""

from __future__ import annotations

import contextlib
import logging
import re
from pathlib import Path

from pypdf import PdfReader

_LOGGER = logging.getLogger("baseline_defense_lab.pdf_extractor")

_WHITESPACE_RE = re.compile(r"\s+")

#: Resource caps  a decompression-bomb PDF must not park
#: the extractor. Pages beyond the cap are skipped; once the total
#: character budget is exhausted no further surface is appended. Both
#: events are recorded in ``surface_lens`` so downstream consumers see
#: that the extraction is partial.
_MAX_PAGES = 500
_MAX_TOTAL_CHARS = 2_000_000


def _clean(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _decode_unicode_tags(text: str) -> str:
    """Decode the U+E0020–U+E007E TAG block back into ASCII.

    This recovers hidden ASCII payloads that some PDFs embed via Unicode
    TAG codepoints, which pypdf otherwise emits literally.
    """
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0xE0020 <= cp <= 0xE007E:
            out.append(chr(cp - 0xE0000))
        else:
            out.append(ch)
    return "".join(out)


#: PDF text render modes that paint no ink  text is in the content stream but
#: invisible to a human reader (a classic injection vector). 3 = neither fill
#: nor stroke; 7 = add-to-clip only. Runs drawn under these modes (or at a
#: zero/negative font size) are dropped during extraction.
_INVISIBLE_RENDER_MODES = frozenset({3, 7})

#: PDF text-showing operators. Visibility is decided at each of these  where
#: the render mode is the one the glyphs are actually painted under  because
#: pypdf delivers the decoded text later in a single batched ``visitor_text``
#: call whose mode reflects any ``0 Tr`` / ``Q`` reset an attacker slips in
#: before ``ET`` (the render-mode-reset bypass).
_TEXT_SHOW_OPS = frozenset({b"Tj", b"TJ", b"'", b'"'})


def _extract_visible_page_text(page) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    """Extract page text, dropping invisibly-rendered runs.

    ``pypdf``'s ``extract_text`` returns *all* text regardless of how it is
    painted, so an attacker can hide an injection with text render mode 3
    (``3 Tr``  invisible) or a zero font size: unseen by a human opening the
    PDF, yet pulled verbatim into the prompt. We follow the text render mode
    through the content stream  honouring the ``q``/``Q`` graphics-state
    stack so a render mode set inside a saved state does not bleed past its
    ``Q``  and evaluate visibility **at each text-show operator**, where the
    mode is the one the glyphs are actually painted under. pypdf hands us the
    decoded text later in one batched callback per text object; if any show in
    that batch ran under an invisible mode the whole batch is dropped, so a
    ``0 Tr`` / ``Q`` reset slipped in before ``ET`` can no longer launder a
    hidden run back into "visible" text.

    Returns ``(visible_text, dropped_char_count)``. Raises only if the
    underlying ``extract_text`` does; the caller falls back to the plain path.
    """
    state = {"mode": 0, "batch_hidden": False}
    saved: list[int] = []
    visible: list[str] = []
    dropped = 0

    def _before(operator, operands, _cm, _tm):  # type: ignore[no-untyped-def]
        if operator == b"q":
            saved.append(state["mode"])
        elif operator == b"Q":
            if saved:
                state["mode"] = saved.pop()
        elif operator == b"Tr" and operands:
            with contextlib.suppress(TypeError, ValueError):
                state["mode"] = int(operands[0])
        elif operator in _TEXT_SHOW_OPS and state["mode"] in _INVISIBLE_RENDER_MODES:
            # A glyph run painted under an invisible render mode. Record it now,
            # at the show operator  not in the batched _text callback below,
            # whose mode may have been reset by a `0 Tr` / `Q` before `ET`. If
            # ANY show in the pending batch was hidden, the whole batch is
            # dropped (fail-closed): a benign PDF does not mix an invisible run
            # with visible text inside one text object.
            state["batch_hidden"] = True

    def _text(text, _cm, _tm, _font, font_size):  # type: ignore[no-untyped-def]
        nonlocal dropped
        hidden = state["batch_hidden"] or (font_size is not None and font_size <= 0)
        if text and hidden:
            dropped += len(text)
        elif text:
            visible.append(text)
        state["batch_hidden"] = False  # reset for the next batched text run

    page.extract_text(visitor_operand_before=_before, visitor_text=_text)
    return "".join(visible), dropped


def extract_pdf_text(path: Path, *, drop_invisible: bool = False) -> tuple[str, dict[str, int]]:
    """Extract a multi-surface text blob from a PDF.

    Parameters
    ----------
    drop_invisible
        When ``True`` (driven by the ``input_sanitizer`` defense) text painted
        with an invisible render mode (3/7) or a zero font size is dropped per
        page  a human never sees it, so it must not reach the prompt. When
        ``False`` (the default plain upload) extraction is faithful and keeps
        every run, so the unguarded baseline still exposes a hidden payload.

    Returns
    -------
    tuple
        ``(text, metadata)`` where the metadata records per-surface character
        counts (and ``invisible_dropped_p{n}`` when runs were dropped) for
        downstream auditing.
    """
    reader = PdfReader(str(path))
    parts: list[str] = []
    surface_lens: dict[str, int] = {}
    total_chars = 0

    for idx, page in enumerate(reader.pages):
        if idx >= _MAX_PAGES:
            surface_lens["truncated_pages"] = len(reader.pages) - _MAX_PAGES
            break
        if total_chars >= _MAX_TOTAL_CHARS:
            surface_lens["truncated_total_chars"] = 1
            break
        dropped_invisible = 0
        page_text = ""
        try:
            if drop_invisible:
                page_text, dropped_invisible = _extract_visible_page_text(page)
            else:
                page_text = page.extract_text() or ""
        except Exception:
            # Hostile/malformed PDFs (or a render-mode parse error) must not
            # abort extraction. Fall back to plain extraction  note this
            # fallback cannot drop invisible runs even when asked to.
            _LOGGER.debug(
                "page %d text extraction failed (drop_invisible=%s)",
                idx + 1,
                drop_invisible,
                exc_info=True,
            )
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
        if dropped_invisible:
            surface_lens[f"invisible_dropped_p{idx + 1}"] = dropped_invisible
        page_text = _decode_unicode_tags(_clean(page_text))
        if page_text:
            parts.append(f"[page {idx + 1}] {page_text}")
            surface_lens[f"page_{idx + 1}"] = len(page_text)
            total_chars += len(page_text)

        annots = page.get("/Annots") or []
        for ann_ref in annots:
            try:
                ann = ann_ref.get_object()
                ann_text = ann.get("/Contents")
                if ann_text:
                    decoded = _decode_unicode_tags(_clean(str(ann_text)))
                    parts.append(f"[annotation p{idx + 1}] {decoded}")
                    surface_lens[f"annotation_p{idx + 1}"] = surface_lens.get(
                        f"annotation_p{idx + 1}", 0
                    ) + len(decoded)
            except Exception:
                _LOGGER.debug("annotation extraction failed on page %d", idx + 1, exc_info=True)
                continue

    meta = reader.metadata or {}
    for key in ("/Title", "/Subject", "/Keywords", "/Creator"):
        value = meta.get(key)
        if value:
            decoded = _decode_unicode_tags(_clean(str(value)))
            parts.append(f"[metadata {key.lstrip('/')}] {decoded}")
            surface_lens[f"metadata_{key.lstrip('/')}"] = len(decoded)

    try:
        outline = reader.outline or []
        outline_titles: list[str] = []

        def _walk(items):  # type: ignore[no-untyped-def]
            for item in items:
                if isinstance(item, list):
                    _walk(item)
                else:
                    title = getattr(item, "title", None)
                    if title:
                        outline_titles.append(_decode_unicode_tags(_clean(str(title))))

        _walk(outline)
        if outline_titles:
            joined = " | ".join(outline_titles)
            parts.append(f"[outline] {joined}")
            surface_lens["outline"] = len(joined)
    except Exception:
        _LOGGER.debug("outline extraction failed", exc_info=True)

    full = "\n\n".join(parts)
    surface_lens["total"] = len(full)
    return full, surface_lens
