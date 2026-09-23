# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Adapter - turn the real ``extract_pdf_text`` output into channel dicts.

The repository's :func:`baseline_defense_lab.pdf_extractor.extract_pdf_text`
returns a ``tuple[str, dict[str, int]]`` - a single flat text blob plus
per-surface character counts. The blob interleaves every surface with a
prefix tag::

    [page 1] <body text>

    [annotation p1] <annotation contents>

    [metadata Title] <title>
    ...
    [outline] <title 1> | <title 2>

The sanitizer, however, wants the four surfaces separated so each can be
quarantined into its own spotlighting channel. :func:`extracted_to_channels`
is the bridge: it accepts whatever ``extract_pdf_text`` produced (the
tuple, or just the blob string, or an already-shaped dict) and always
returns the canonical four-channel dict::

    {"body": str,
     "metadata": {"title": str, "subject": str, "keywords": str, "creator": str},
     "outline": list[str],
     "annotations": list[str]}

This keeps ``extractor.py`` untouched (its TAG-block decoding stays the
single source of truth for PDF walking) while still giving the sanitizer
the structured shape the spec mandates.
"""

from __future__ import annotations

import re
from typing import Any

#: The four metadata sub-keys the extractor surfaces (``/Title`` etc.).
METADATA_KEYS: tuple[str, ...] = ("title", "subject", "keywords", "creator")

#: One blob part: ``[<tag>] <content>``. ``extractor._clean`` collapses all
#: whitespace inside a part to single spaces, so a part never contains the
#: ``\n\n`` separator - the split below is therefore unambiguous.
_PART_RE = re.compile(
    r"^\[(page \d+|annotation p\d+|metadata \w+|outline)\]\s?(.*)$",
    re.DOTALL,
)


def _normalise_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Coerce an already-shaped dict into the canonical channel layout."""
    md = d.get("metadata") or {}
    return {
        "body": str(d.get("body", "") or ""),
        "metadata": {k: str(md.get(k, "") or "") for k in METADATA_KEYS},
        "outline": [str(x) for x in (d.get("outline") or [])],
        "annotations": [str(x) for x in (d.get("annotations") or [])],
    }


def _parse_blob(blob: str) -> dict[str, Any]:
    """Parse the prefixed flat blob back into the four channels."""
    body_parts: list[str] = []
    annotations: list[str] = []
    outline: list[str] = []
    metadata: dict[str, str] = {k: "" for k in METADATA_KEYS}

    for chunk in blob.split("\n\n"):
        stripped = chunk.strip()
        if not stripped:
            continue
        match = _PART_RE.match(stripped)
        if match is None:
            # Untagged text - be conservative and treat it as body content.
            body_parts.append(stripped)
            continue
        tag, content = match.group(1), match.group(2).strip()
        if tag.startswith("page "):
            body_parts.append(content)
        elif tag.startswith("annotation "):
            annotations.append(content)
        elif tag.startswith("metadata "):
            key = tag.split(" ", 1)[1].lower()
            if key in metadata:
                metadata[key] = content
        elif tag == "outline":
            outline = [t.strip() for t in content.split(" | ") if t.strip()]

    return {
        "body": "\n\n".join(body_parts),
        "metadata": metadata,
        "outline": outline,
        "annotations": annotations,
    }


def extracted_to_channels(extracted: Any) -> dict[str, Any]:
    """Normalise any ``extract_pdf_text`` output into the channel dict.

    Parameters
    ----------
    extracted
        One of:

        * the ``(text, surface_lens)`` tuple ``extract_pdf_text`` returns,
        * the flat blob ``str`` on its own,
        * an already-shaped ``{"body", "metadata", "outline", "annotations"}``
          dict (passed through after key/shape normalisation).

    Returns
    -------
    dict
        The canonical four-channel dict.
    """
    if isinstance(extracted, dict):
        return _normalise_dict(extracted)
    if isinstance(extracted, tuple):
        blob = extracted[0] if extracted else ""
        return _parse_blob(str(blob or ""))
    return _parse_blob(str(extracted or ""))
