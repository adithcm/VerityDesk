# Phase 2 Milestone 2.1: Repo And Tooling Scaffold

Status: Complete

## Goal

Create the first runnable project structure for InvestorAgent.

## Included In This Milestone

- `frontend/` Next.js app with TypeScript and Tailwind configuration.
- `backend/` FastAPI app with a health endpoint.
- Root `.env.example`.
- Root `docker-compose.yml`.
- Root `Makefile` with local development commands.
- Dockerfiles for frontend and backend.
- Ignore files for local dependencies, build output, data, and secrets.

## Runtime Requirements

- Node.js `>=20.9.0` for the frontend.
- Python `>=3.11` for the backend.

## Not Included Yet

- SQLite models and migrations.
- Source catalog implementation.
- Real ingestion from APIs or RSS feeds.
- Real agent orchestration.
- Full dashboard screens.
- Desktop packaging.

## Local Commands

Backend:

```bash
cd backend
python3 -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker:

```bash
docker compose up --build
```

## Definition Of Done

- Repo has `frontend/` and `backend/` directories.
- Backend has a FastAPI health endpoint.
- Frontend has a Next.js landing scaffold.
- Root commands and env example exist.
- Docker Compose describes the local stack.
- README links to the milestone and explains local setup.
