# Phase 3

Status: In progress

Phase 3 connects InvestorAgent to real data by adding ingestion storage, RSS/API fetchers, source scheduling, freshness tracking, and UI visibility for source health.

## Completed Milestones

- [Milestone 3.1: Ingestion Data Model](milestones/3.1-ingestion-data-model.md)
- [Milestone 3.2: RSS Ingestion Foundation](milestones/3.2-rss-ingestion-foundation.md)
- [Milestone 3.3: Official API Ingestion Foundation](milestones/3.3-official-api-ingestion-foundation.md)

## Next Milestone

### Milestone 3.4: Source Scheduler

Goal: add a local scheduler and backend-triggered ingestion runner so sources can run daily or on demand.

Expected deliverables:

- Local scheduler service.
- Manual backend endpoint for ingestion runs.
- Source selection by source ID or source type.
- Run locking to avoid overlapping ingestion.
- Daily schedule configuration.
- Tests for scheduler triggering, run logging, and failure isolation.

## Later Phase 3 Milestones

- Milestone 3.5: Source Health And Freshness API.
- Milestone 3.6: Frontend Ingestion Visibility.
- Milestone 3.7: Phase 3 Validation And Docs.
