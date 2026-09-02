# Phase 3

Status: In progress

Phase 3 connects InvestorAgent to real data by adding ingestion storage, RSS/API fetchers, source scheduling, freshness tracking, and UI visibility for source health.

## Completed Milestones

- [Milestone 3.1: Ingestion Data Model](milestones/3.1-ingestion-data-model.md)
- [Milestone 3.2: RSS Ingestion Foundation](milestones/3.2-rss-ingestion-foundation.md)

## Next Milestone

### Milestone 3.3: Official API Ingestion Foundation

Goal: add connector structure for official APIs and datasets, starting with SEC data APIs and selected macro/housing data sources.

Expected deliverables:

- Official API connector interface.
- SEC company submissions connector foundation.
- FRED connector foundation.
- Census connector foundation.
- FHFA dataset connector foundation.
- Freddie Mac PMMS dataset connector foundation.
- Structured observation persistence.
- Tests for response normalization and missing API-key handling.

## Later Phase 3 Milestones

- Milestone 3.4: Source Scheduler.
- Milestone 3.5: Source Health And Freshness API.
- Milestone 3.6: Frontend Ingestion Visibility.
- Milestone 3.7: Phase 3 Validation And Docs.
