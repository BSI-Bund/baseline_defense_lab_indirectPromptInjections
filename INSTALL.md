# Installation

This document describes how to build, configure, and run Baseline-Defense-Lab, and how to reproduce its quality checks. For an overview of the project see [README.md](README.md).

## Table of contents

- [Prerequisites](#prerequisites)
- [Option A - full Docker stack (recommended)](#option-a--full-docker-stack-recommended)
- [Option B - local development without Docker](#option-b--local-development-without-docker)
- [Configuration (environment variables)](#configuration-environment-variables)
- [Generation defaults](#generation-defaults)
- [Build environment and steps](#build-environment-and-steps)
- [Running the checks](#running-the-checks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- **[Ollama](https://ollama.com)** - the local model runtime. The default model is `gemma3:12b`. A GPU is optional but strongly recommended (CPU inference is ~10–20× slower).
- **For the Docker stack:** Docker with Compose v2. Optional GPU passthrough needs Docker Desktop with WSL2 + the NVIDIA Container Toolkit (or a native Linux host with the toolkit).
- **For local development:** Python **3.11+** (CI and the Docker images use **3.12**) and **Node 20**.

## Option A - full Docker stack (recommended)

Brings up four services with a single command, all bound to the loopback interface: `ollama` (model runtime), `ollama-init` (one-shot model pull), `backend` (FastAPI + bundled SPA), and `frontend` (nginx serving the SPA and reverse-proxying `/api`).

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Published ports (see [`docker/docker-compose.yml`](docker/docker-compose.yml)):

| Service | URL / port | Notes |
|---------|-----------|-------|
| Frontend (nginx) | `http://127.0.0.1:4201` | Recommended entry point |
| Backend-served SPA | `http://127.0.0.1:8002` | Same app, single port |
| Ollama (debug) | `127.0.0.1:11436` | Manual debugging only |

Select the auto-pulled model with `OLLAMA_MODEL`, or pull several at once with `OLLAMA_MODELS`:

```bash
OLLAMA_MODEL=qwen3:30b docker compose -f docker/docker-compose.yml up -d --build
OLLAMA_MODELS="gemma3:12b qwen3:30b qwen3:14b" docker compose -f docker/docker-compose.yml up -d --build
```

The pulled model is cached in the `ollama_data` named volume and survives `docker compose down`. Use `docker compose ... down -v` to force a fresh pull. On a CPU-only host, comment out the `deploy:` GPU block in the compose file.

## Option B - local development without Docker

You need a local Ollama reachable at `http://localhost:11434` with at least one model pulled (e.g. `ollama pull gemma3:12b`).

### Backend

```bash
# from the repository root
python -m venv .venv
# Linux/macOS:  source .venv/bin/activate
# Windows (PowerShell):  .venv\Scripts\Activate.ps1

# Editable install. The [dev] extra includes the server and langchain extras
# plus Ruff and mypy; use [server] for the API only, or [server,langchain] to
# include the second engine path.
python -m pip install -e "backend[dev]"

# Run the API (auto-reload), which talks to Ollama on localhost:11434:
uvicorn baseline_defense_lab.server.app:app --reload --port 8000
```

The backend serves on `http://127.0.0.1:8000`. It will serve the built Angular SPA at `/` if one exists under `frontend/dist/...`; otherwise run the dev server below.

### Frontend

```bash
cd frontend
npm install -g npm@11      # pin npm 11 (see Troubleshooting)
npm ci
npm start                  # Angular dev server on http://localhost:4200
```

The dev server proxies `/api` to `http://localhost:8000` (see [`frontend/proxy.conf.json`](frontend/proxy.conf.json)), so run the backend in parallel.

## Configuration (environment variables)

All configuration is via environment variables; copy [`.env.example`](.env.example) to `.env` and adjust as needed. **Never put real secrets here** - this stack has no authentication and is for local/loopback use only.

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_URL` | `http://localhost:11434` (app); `http://ollama:11434` (compose) | Base URL the backend uses to reach Ollama. |
| `OLLAMA_MODEL` | `gemma3:12b` | Default model pulled by `ollama-init` and offered in the UI. |
| `OLLAMA_MODELS` | *(empty)* | Optional space/comma-separated list to pull several models; takes precedence over `OLLAMA_MODEL`. |
| `CORS_ORIGINS` | `http://localhost:4200,http://127.0.0.1:4200,http://localhost:8000,http://127.0.0.1:8000` (app default); the bundled compose injects the `4201`/`8002` origins | Comma-separated CORS allowlist. **Never** use a wildcard on this unauthenticated API. |
| `BDL_FRONTEND_DIR` | *(unset → resolved relative to the repo)*; `/app/frontend_dist` in Docker | Explicit path to the built Angular SPA served by FastAPI. |
| `BDL_MODEL_ALLOWLIST` | *(empty = any valid Ollama tag)* | Optional comma-separated model allowlist; a non-allowed model in `/api/chat[_langchain]` returns HTTP 400. |
| `BDL_DEBUG` | *(unset = off)* | Opt-in verbose backend debug logging (`1`/`true`/`yes`/`on`). Redacts attacker-controlled document text; loopback dev only. |
| `LOG_LEVEL` | *(unset)* | Log-level override for the backend logger (e.g. `DEBUG`, `INFO`); `BDL_DEBUG=1` alone implies `DEBUG`. |

> Note: the in-code `CORS_ORIGINS` default lists the **local-development** ports (`4200`/`8000`). The bundled Docker stack serves on `4201`/`8002` and injects a matching allowlist, so the default only applies to the non-Docker dev flow.

## Generation defaults

Generation parameters are fixed server-side and are **not** user-tunable in the UI (single source of truth in [`backend/src/baseline_defense_lab/server/app.py`](backend/src/baseline_defense_lab/server/app.py)). `GET /api/defaults` returns the first four:

| Parameter | Value |
|-----------|-------|
| `seed` | `17` (pinned for reproducible demos; `0` disables pinning) |
| `num_predict` | `4096` |
| `temperature` | `0.0` |
| `top_p` | `1.0` |
| `num_ctx` | `25000` (server default `DEFAULT_NUM_CTX`; not returned by `/api/defaults`) |

## Build environment and steps

- **Python package** - build backend [Hatchling](https://hatch.pypa.io) (`hatchling>=1.27`); the wheel packages `src/baseline_defense_lab`. For development, the editable install above is sufficient. The Docker image installs `./backend[server,langchain]` on `python:3.12-slim`.
- **Frontend** - Angular CLI 18 on `node:20-alpine`. Production build:

  ```bash
  cd frontend
  npm ci
  npx ng build                       # default = production
  # output: frontend/dist/baseline-defense-lab-frontend/browser
  ```

- **Container images (pinned)** - `python:3.12-slim`, `node:20-alpine`, `nginx:1.27-alpine`, `ollama/ollama:0.24.0`. See [`docker/`](docker).

## Running the checks

> The checks below are the ones the project holds itself to. They are fully reproducible on a clean checkout.

```bash
# 1. Python lint
python -m pip install -e "backend[dev]"
python -m ruff check backend/src

# 2. Frontend production build
cd frontend && npm install -g npm@11 && npm ci && npx ng build && cd ..
```

`mypy` is available (`python -m mypy backend/src`) but is not yet part of CI.

## Troubleshooting

- **`npm ci` fails on a fresh Node 20 install.** Node 20 ships npm 10.8.2, which mis-resolves an Angular dependency conflict and then rejects its own lockfile. Pin npm 11 first: `npm install -g npm@11`.
- **`POST /api/chat_langchain` returns HTTP 501.** The `[langchain]` extra is not installed: `python -m pip install -e "backend[langchain]"`.
- **`reasoning_active` is `false`.** The selected model (e.g. `gemma3`) does not support a reasoning/think channel; the pipeline falls back to a normal call.
- **Inference is very slow.** You are likely running on CPU. Enable GPU passthrough (NVIDIA Container Toolkit) or run on a GPU host for acceptable latency.
