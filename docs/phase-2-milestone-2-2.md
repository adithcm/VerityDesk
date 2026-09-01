# Phase 2 Milestone 2.2: Backend Foundation

Status: Complete

## Goal

Turn the backend scaffold into a modular FastAPI service foundation.

## Included In This Milestone

- Modular API package structure:
  - `app/api/`
  - `app/api/v1/`
  - `app/api/v1/router.py`
  - `app/api/v1/endpoints/`
  - `app/schemas/`
  - `app/services/`
- FastAPI app factory in `app/main.py`.
- Central settings in `app/core/config.py`.
- Logging configuration in `app/core/logging.py`.
- CORS origins derived from settings.
- System endpoints:
  - `GET /health`
  - `GET /api/v1/health`
  - `GET /api/v1/version`
- Shared response schemas.
- Backend tests for health, version, CORS, and settings behavior.

## Not Included Yet

- SQLite models and migrations.
- Source catalog endpoint implementation.
- Agent contracts and guardrail modules.
- Live source ingestion.

## Backend Commands

Install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -e backend[dev]
```

Run tests:

```bash
cd backend
../.venv/bin/pytest
```

Run lint:

```bash
cd backend
../.venv/bin/ruff check app tests
```

Run the backend:

```bash
make backend-dev
```

## Definition Of Done

- Backend has a clean modular FastAPI structure.
- Root and versioned health endpoints work.
- Version endpoint works.
- Settings are centralized.
- CORS is configured from settings.
- Logging is configured.
- Backend tests pass.
- Backend lint passes.
