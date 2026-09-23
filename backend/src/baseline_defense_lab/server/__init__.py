# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Optional FastAPI backend for the manual testing UI.

Importing this subpackage requires the ``server`` extras
(``pip install '.[server]'``).
"""

from .app import create_app

__all__ = ["create_app"]
