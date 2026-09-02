# Phase 3

Status: In progress

Phase 3 connects InvestorAgent to real data by adding ingestion storage, RSS/API fetchers, source scheduling, freshness tracking, and UI visibility for source health.

## Completed Milestones

- [Milestone 3.1: Ingestion Data Model](milestones/3.1-ingestion-data-model.md)

## Next Milestone

### Milestone 3.2: RSS Ingestion Foundation

Goal: fetch RSS feeds from configured sources and normalize feed entries into the ingestion data model.

Expected deliverables:

- RSS fetcher service.
- Normalized feed entry object.
- BBC News RSS connector.
- SEC EDGAR RSS connector.
- Article metadata persistence.
- Deduplication by URL, canonical URL, content hash, and external ID.
- Ingestion run logging for RSS fetches.
- Tests for parsing, persistence, and duplicate handling.

## Later Phase 3 Milestones

- Milestone 3.3: Official API Ingestion Foundation.
- Milestone 3.4: Source Scheduler.
- Milestone 3.5: Source Health And Freshness API.
- Milestone 3.6: Frontend Ingestion Visibility.
- Milestone 3.7: Phase 3 Validation And Docs.
