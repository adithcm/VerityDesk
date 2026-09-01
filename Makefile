.PHONY: node-install backend-dev frontend-dev frontend-build frontend-typecheck compose-up compose-down

LOCAL_NODE_BIN := $(CURDIR)/.runtime/node-v22.23.2-darwin-arm64/bin

node-install:
	bash scripts/install-local-node.sh

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

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
