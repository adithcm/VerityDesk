# Phase 2 Milestone 2.3: Database Foundation

Status: Complete

## Goal

Add the local SQLite persistence layer that later source catalog, ingestion, report, citation, and agent features can build on.

## Included In This Milestone

- Backend dependencies:
  - SQLAlchemy
  - Alembic
- Database package:
  - `app/db/base.py`
  - `app/db/models.py`
  - `app/db/session.py`
- SQLAlchemy models:
  - `Source`
  - `Article`
  - `Company`
  - `EconomicObservation`
  - `Report`
  - `Citation`
  - `AgentRun`
  - `UserSettings`
- Alembic setup:
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/script.py.mako`
  - initial migration `0001_initial_schema.py`
- Makefile commands:
  - `make backend-test`
  - `make backend-lint`
  - `make db-upgrade`
  - `make db-downgrade`
- Tests for:
  - model metadata
  - SQLite engine creation
  - model insert/relationship smoke test
  - Alembic upgrade against a temporary SQLite database

## Not Included Yet

- Source catalog seed data.
- Source catalog API endpoint.
- Ingestion jobs.
- Agent persistence endpoints.
- Settings API backed by the database.

## Database Commands

Install backend dependencies:

```bash
.venv/bin/pip install -e backend[dev]
```

Run the initial migration:

```bash
make db-upgrade
```

Run backend tests:

```bash
make backend-test
```

Run backend lint:

```bash
make backend-lint
```

## Definition Of Done

- SQLite configuration works.
- SQLAlchemy models exist for the Phase 1 data model.
- Alembic can create the initial database schema.
- Database tests pass.
- Backend tests pass.
- Backend lint passes.
- Docs are updated.
