# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
#
# Two-stage build: Angular CLI compiles the SPA, then a slim Python image
# installs the backend package and serves FastAPI + the pre-built ``dist/``
# directory as static files.
#
# Build context is the repository root (see docker-compose.yml ``context: ..``)
# so this Dockerfile can reach both ``backend/`` and ``frontend/``.

# --- Stage 1: build the Angular frontend -----------------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /workspace/frontend

# Install npm deps first so the layer cache survives source edits.
# ``npm ci`` (not ``npm install``) - reproducible builds from the lockfile.
# node:20-alpine ships npm 10.8.2, which writes an inconsistent lockfile for
# the Angular chokidar 3-vs-4 dependency conflict and then rejects it in
# ``npm ci``; pin npm 11 (the version the lockfile was generated with) so the
# strict install succeeds.
COPY frontend/package.json frontend/package-lock.json /workspace/frontend/
RUN npm install -g npm@11 \
 && npm ci --no-audit --no-fund --ignore-scripts \
 && npm rebuild

# Now copy the rest of the Angular project and produce the production bundle
# at /workspace/frontend/dist/baseline-defense-lab-frontend/browser.
COPY frontend /workspace/frontend
RUN npx ng build --configuration production

# --- Stage 2: Python runtime serving FastAPI + the built SPA --------------
FROM python:3.12-slim AS runtime

# EUPL-1.2 Art. 3 and Art. 5 ("Provision of Source Code") require the source to
# be available or a repository to be indicated. The OCI source label carries
# that indication with the image itself, so a recipient who only has the image
# can still find the Source Code.
LABEL org.opencontainers.image.title="Baseline-Defense-Lab (backend + bundled SPA)" \
      org.opencontainers.image.source="<Projekt-URL>" \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.vendor="Bundesamt für Sicherheit in der Informationstechnik (BSI)"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_URL=http://ollama:11434 \
    BDL_FRONTEND_DIR=/app/frontend_dist

WORKDIR /app

# Python deps in their own layer. The backend package lives under ./backend and
# is self-contained: hatchling needs its ``README.md`` (long description) and its
# ``LICENSE`` (declared via ``license-files``) inside the project directory at
# build time, so both are copied alongside the pyproject.
COPY backend/pyproject.toml backend/README.md backend/LICENSE /app/backend/
COPY backend/src /app/backend/src
# Install the FastAPI server extras and the LangChain extras so both the
# direct ``/api/chat`` path and the ``--engine langchain`` path work.
RUN pip install --upgrade pip \
 && pip install "./backend[server,langchain]"

# Static frontend, baked in from the build stage.
COPY --from=frontend-build /workspace/frontend/dist/baseline-defense-lab-frontend/browser /app/frontend_dist

# Attribution for the bundled npm dependencies. ``ng build`` writes
# ``3rdpartylicenses.txt`` to the *root* of the output directory, one level above
# ``browser/``, so it needs its own COPY - otherwise the image serves MIT- and
# Apache-2.0-licensed bundle code with no notice. It lands in the static root,
# which app.py serves at /3rdpartylicenses.txt via an explicit route.
COPY --from=frontend-build /workspace/frontend/dist/baseline-defense-lab-frontend/3rdpartylicenses.txt /app/frontend_dist/3rdpartylicenses.txt

# EUPL-1.2 Art. 5 requires a copy of the Licence to accompany every copy of the
# Work. ``pip install`` already puts one in the wheel's dist-info; these make it
# findable at the conventional image root too, and the copies in the static root
# are what the /LICENSE and /THIRD-PARTY-NOTICES.md routes serve - same paths as
# the nginx image, so the two deployments answer identically.
COPY --chmod=0644 LICENSE /app/LICENSE
COPY --chmod=0644 THIRD-PARTY-NOTICES.md /app/THIRD-PARTY-NOTICES.md
COPY --chmod=0644 LICENSE /app/frontend_dist/LICENSE
COPY --chmod=0644 THIRD-PARTY-NOTICES.md /app/frontend_dist/THIRD-PARTY-NOTICES.md

COPY docker/healthcheck.py /app/healthcheck.py

# Drop root: uvicorn binds 8000 (unprivileged), the app only needs read
# access to /app plus tmpfile writes.
RUN useradd --create-home --uid 10001 bdl \
 && chown -R bdl:bdl /app
USER bdl

EXPOSE 8000

# 503 = "up but Ollama unreachable" - still a healthy *container*; the
# HTTPError handling lives in healthcheck.py (urlopen raises on 503).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "/app/healthcheck.py"]

# Bind 0.0.0.0 *inside the container*; compose only publishes it on the host
# loopback (127.0.0.1:8000). The two are independent - see docker-compose.yml.
CMD ["uvicorn", "baseline_defense_lab.server.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
