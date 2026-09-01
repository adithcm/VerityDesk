.PHONY: backend-dev frontend-dev compose-up compose-down

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev

compose-up:
	docker compose up --build

compose-down:
	docker compose down
