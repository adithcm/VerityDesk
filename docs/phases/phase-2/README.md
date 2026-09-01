# Phase 2

Status: In progress

Phase 2 builds the runnable application scaffold: frontend, backend, database foundation, source catalog foundation, agent contracts, guardrail contracts, and first UI shell.

## Completed Milestones

- [Milestone 2.1: Repo And Tooling Scaffold](milestones/2.1-repo-and-tooling-scaffold.md)
- [Milestone 2.2: Backend Foundation](milestones/2.2-backend-foundation.md)
- [Milestone 2.3: Database Foundation](milestones/2.3-database-foundation.md)

## Next Milestone

### Milestone 2.4: Source Catalog Foundation

Goal: add the static v1 source catalog and expose it through the backend.

Expected deliverables:

- Source catalog config file.
- Pydantic schemas for source catalog responses.
- Service for loading and validating configured sources.
- `GET /api/v1/sources` endpoint.
- Seed entries for:
  - BBC RSS
  - SEC data APIs
  - SEC EDGAR RSS
  - FRED
  - U.S. Census Economic Indicators
  - FHFA HPI
  - Freddie Mac PMMS
  - Company investor relations pages
  - Optional Alpha Vantage
  - Optional Finnhub
  - Optional NewsAPI
  - Optional GDELT
- Tests for source loading and the sources endpoint.
- Docs for source metadata fields and storage policies.
