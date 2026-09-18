.PHONY: node-install app-dev backend-dev backend-test backend-lint db-upgrade db-downgrade rss-ingest official-api-ingest frontend-dev frontend-build frontend-typecheck desktop-dev desktop-prod desktop-build desktop-check compose-up compose-down postgres-up postgres-shell postgres-tables

LOCAL_NODE_BIN := $(CURDIR)/.runtime/node-v22.23.2-darwin-arm64/bin

node-install:
	bash scripts/install-local-node.sh

app-dev:
	bash scripts/start-local.sh

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

official-api-ingest:
	cd backend && ../.venv/bin/python -m app.cli.ingest_official_apis

frontend-dev:
	cd frontend && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run dev

frontend-build:
	cd frontend && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run build

frontend-typecheck:
	cd frontend && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run typecheck

desktop-dev:
	cd desktop && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run dev

desktop-prod:
	$(MAKE) frontend-build
	cd desktop && PATH="$(LOCAL_NODE_BIN):$$PATH" VERITYDESK_DESKTOP_MODE=production npm run dev

desktop-build:
	$(MAKE) frontend-build
	$(MAKE) desktop-check

desktop-check:
	cd desktop && PATH="$(LOCAL_NODE_BIN):$$PATH" npm run check

compose-up:
	docker compose up --build

compose-down:
	docker compose down

postgres-up:
	docker compose up -d postgres

postgres-shell:
	docker compose exec postgres psql -U veritydesk -d veritydesk

postgres-tables:
	docker compose exec postgres psql -U veritydesk -d veritydesk -c "\dt"
