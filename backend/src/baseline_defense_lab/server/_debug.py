# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Opt-in debug instrumentation for the backend (default OFF).

Active only when ``BDL_DEBUG`` or ``LOG_LEVEL`` is set in the environment. This
module never changes runtime behaviour: it only raises logging verbosity and
provides redaction helpers. The response envelope and the egress/canary
decision are untouched. Attacker-controlled document text is truncated before
logging; canary tokens and model answer text are never logged at all.
"""

from __future__ import annotations

import logging
import os

_DEBUG = os.environ.get("BDL_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
_LOG_LEVEL = os.environ.get("LOG_LEVEL", "").strip().upper()


def is_debug() -> bool:
    """True when verbose debug instrumentation is enabled (``BDL_DEBUG``)."""
    return _DEBUG


def configure_logging() -> None:
    """Configure the package logger only when opted in; otherwise a no-op.

    With neither flag set this returns immediately, so logging behaves exactly
    as before. ``BDL_DEBUG=1`` implies DEBUG; ``LOG_LEVEL`` overrides the
    threshold. A dedicated handler on the package logger (propagate off) keeps
    output visible and un-duplicated under uvicorn's own logging config.
    """
    if not _DEBUG and not _LOG_LEVEL:
        return
    level = getattr(logging, _LOG_LEVEL or "DEBUG", logging.DEBUG)
    pkg = logging.getLogger("baseline_defense_lab")
    pkg.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in pkg.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        pkg.addHandler(handler)
    pkg.propagate = False


def redact(text: str | None, *, keep: int = 120) -> str:
    """Render attacker-controlled text for logs as length + short prefix only."""
    if not text:
        return "<empty>"
    prefix = " ".join(text[:keep].split())
    suffix = "…" if len(text) > keep else ""
    return f"<{len(text)} chars> {prefix!r}{suffix}"
