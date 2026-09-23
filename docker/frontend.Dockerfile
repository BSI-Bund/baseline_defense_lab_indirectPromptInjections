# SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI)
# SPDX-License-Identifier: EUPL-1.2
#
# Standalone frontend image: the Angular SPA served by nginx, with /api/*
# transparently reverse-proxied to the FastAPI backend container.
#
# The backend image (``backend.Dockerfile``) also bakes a copy of the SPA in
# for the single-port deployment. This image exists so docker-compose can spin
# the frontend up as its own service, to inspect / iterate on the two tiers
# independently.
#
# Build context is the repository root (see docker-compose.yml ``context: ..``).

# --- Stage 1: build the Angular bundle ------------------------------------
FROM node:20-alpine AS build

WORKDIR /workspace/frontend

# ``npm ci`` for a reproducible install straight from the lockfile. Pin npm 11:
# node:20-alpine ships npm 10.8.2, which mis-resolves the Angular chokidar
# 3-vs-4 conflict into a lockfile its own ``npm ci`` then rejects.
COPY frontend/package.json frontend/package-lock.json /workspace/frontend/
RUN npm install -g npm@11 \
 && npm ci --no-audit --no-fund --ignore-scripts \
 && npm rebuild

COPY frontend /workspace/frontend
RUN npx ng build --configuration production

# --- Stage 2: nginx serving the bundle ------------------------------------
FROM nginx:1.27-alpine AS runtime

# This image distributes Executable Code (the built SPA bundle). EUPL-1.2 Art. 3
# and Art. 5 require the Source Code to be provided or a repository indicated;
# the OCI source label does that for a recipient who only has the image.
LABEL org.opencontainers.image.title="Baseline-Defense-Lab (frontend)" \
      org.opencontainers.image.source="<Projekt-URL>" \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.vendor="Bundesamt für Sicherheit in der Informationstechnik (BSI)"

# Drop the stock default site and install our SPA + reverse-proxy config.
RUN rm /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/conf.d/frontend.conf

# Static SPA: copy the built ``browser/`` artefacts to nginx's webroot.
COPY --from=build /workspace/frontend/dist/baseline-defense-lab-frontend/browser /usr/share/nginx/html

# Attribution for the bundled npm dependencies. ``ng build`` collects their
# copyright notices and licence texts into ``3rdpartylicenses.txt``, but writes
# it to the *root* of the output directory - NOT into ``browser/`` - so it needs
# its own COPY or it silently stays behind in the build stage. Without it the
# image would ship MIT- and Apache-2.0-licensed code (Angular, RxJS, zone.js,
# tslib) with no notice at all. nginx serves it at /3rdpartylicenses.txt.
COPY --from=build /workspace/frontend/dist/baseline-defense-lab-frontend/3rdpartylicenses.txt /usr/share/nginx/html/3rdpartylicenses.txt

# EUPL-1.2 Art. 5 requires a copy of the Licence to accompany every copy of the
# Work, so the image carries its own instead of relying on the repository.
COPY --chmod=0644 LICENSE /usr/share/nginx/html/LICENSE
COPY --chmod=0644 THIRD-PARTY-NOTICES.md /usr/share/nginx/html/THIRD-PARTY-NOTICES.md

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O - http://127.0.0.1/healthz >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
