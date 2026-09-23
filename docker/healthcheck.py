# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
"""Container healthcheck for the backend.

200 = healthy. 503 = degraded-but-up (Ollama unreachable) - still a healthy
*container*, so it must not flap the orchestrator. Note that
``urllib.request.urlopen`` raises ``HTTPError`` for 503, so the status has to
be read on the exception path; checking ``r.status in (200, 503)`` on the
success path alone is dead code.
"""

import sys
import urllib.error
import urllib.request

try:
    r = urllib.request.urlopen("http://127.0.0.1:8000/api/healthz", timeout=3)
    sys.exit(0 if r.status == 200 else 1)
except urllib.error.HTTPError as exc:
    sys.exit(0 if exc.code == 503 else 1)
except Exception:  # noqa: BLE001 - any other failure is unhealthy
    sys.exit(1)
