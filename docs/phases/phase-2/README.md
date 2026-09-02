# Phase 2

Status: In progress

Phase 2 builds the runnable application scaffold: frontend, backend, database foundation, source catalog foundation, agent contracts, guardrail contracts, and first UI shell.

## Completed Milestones

- [Milestone 2.1: Repo And Tooling Scaffold](milestones/2.1-repo-and-tooling-scaffold.md)
- [Milestone 2.2: Backend Foundation](milestones/2.2-backend-foundation.md)
- [Milestone 2.3: Database Foundation](milestones/2.3-database-foundation.md)
- [Milestone 2.4: Source Catalog Foundation](milestones/2.4-source-catalog-foundation.md)
- [Milestone 2.5: Agent And Guardrail Contracts](milestones/2.5-agent-and-guardrail-contracts.md)

## Next Milestone

### Milestone 2.6: Frontend Shell

Goal: add the first navigable frontend shell and connect core read/query screens to the backend scaffold.

Expected deliverables:

- App layout and primary navigation.
- Dashboard page.
- Daily Briefing page.
- Sources page connected to `GET /api/v1/sources`.
- Watchlist page scaffold.
- Agent Chat page connected to `POST /api/v1/agents/query`.
- Settings page scaffold.
- Visible investment disclaimer in strategy-oriented surfaces.
- Basic loading, empty, and error states.
