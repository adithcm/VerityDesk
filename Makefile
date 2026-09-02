.PHONY: node-install backend-dev backend-test backend-lint db-upgrade db-downgrade rss-ingest frontend-dev frontend-build frontend-typecheck compose-up compose-down

LOCAL_NODE_BIN := $(CURDIR)/.runtime/node-v22.23.2-darwin-arm64/bin

node-install:
	bash scripts/install-local-node.sh

backend-dev:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test:
	cd backend && ../.venv/bin/pytest

backend-lint:
	cd backend && ../.venv/bin/ruff check app tests

db-upgrade:
	mkdir -p backend/data
	cd backend && ../.venv/bin/alembic upgrade head

db-downgrade:
	cd backend && ../.venv/bin/alembic downgrade -1

rss-ingest:
	cd backend && ../.venv/bin/python -m app.cli.ingest_rss

frontend-dev:
	cd frontend && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run dev

frontend-build:
	cd frontend && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run build

frontend-typecheck:
	cd frontend && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run typecheck

compose-up:
	docker compose up --build

compose-down:
	docker compose down
