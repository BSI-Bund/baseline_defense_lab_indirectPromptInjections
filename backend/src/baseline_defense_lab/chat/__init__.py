# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Minimal chat-completion client used by the direct (native-Ollama) engine path."""

from .client import OllamaChatClient, OllamaChatError

__all__ = ["OllamaChatClient", "OllamaChatError"]
