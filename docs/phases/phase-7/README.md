# Phase 7: Source Expansion And Parser Completion

Status: Planned

## Goal

Finish scaffolded API connectors and broaden credible data coverage so the app can answer more flexible, real-world questions without the user manually checking multiple websites.

This phase must happen before desktop packaging because the app should not be packaged as a polished desktop product while important data sources still say scaffolded or parser-needed.

## User Feedback To Address

- Some API-key/source items still say scaffolded.
- Some parsers still need to be created.
- The app cannot yet answer regional questions well, such as mortgage rates for Arizona.
- The agent is too limited by currently stored local data.
- The app should retrieve from more credible sources automatically.
- The user should not need to know which site or API contains the answer.

## Source Priorities

### Official And Government

- Census Economic Indicators
- FHFA House Price Index
- Freddie Mac PMMS
- FRED series expansion
- SEC company data and filings

### Market And Company APIs

- Alpha Vantage
- Finnhub
- NewsAPI
- GDELT

### Housing And Regional Data

- Mortgage rate data.
- Home price indexes.
- Housing supply, permits, starts, and regional housing indicators.
- State/metro support where sources provide it.
- Clear national-vs-local distinction when only national data is available.

## Carryover From Phase 6

Phase 6 made scaffolded, missing-key, parser-needed, stale, and failed states easier to understand in the UI. Phase 7 should now make those statuses more real by resolving as many source gaps as possible.

Specific carryover items:

- Replace "scaffolded only" with working ingestion where sources are available and compliant.
- Replace "parser not implemented" with tested parsers for Census, FHFA, and Freddie Mac where source access permits.
- Keep optional providers clean when API keys are missing.
- Add clearer source coverage notes when data is national only and cannot answer a local/regional question.
- Improve user examples such as:
  - "What are mortgage rates in AZ?"
  - "What are mortgage rates in Phoenix?"
  - "How is housing affordability changing in Arizona?"

## Milestones

### 7.1 Source Status Audit

Status: Complete

- List every source in the catalog.
- Mark each as working, missing key, scaffolded, parser-needed, optional, or deferred.
- Update docs and UI source metadata.
- Confirm which sources require manual keys.

### 7.2 Census Parser Completion

Status: Complete

- Implement Census Economic Indicators parsing.
- Normalize observations into existing economic observation models.
- Add tests for success, missing key, empty response, and malformed response.

### 7.3 FHFA Parser Completion

Status: Complete

- Implement FHFA HPI parsing.
- Normalize regions and periods.
- Add tests for national, state, and metro-style records where available.

### 7.4 Freddie Mac PMMS Parser Completion

Status: Complete

- Implement Freddie Mac PMMS parsing.
- Normalize mortgage rate series and release dates.
- Add tests for retrieval, parsing, deduplication, and source health.

### 7.5 Optional Provider Connectors

- Add or complete optional providers:
  - Alpha Vantage
  - Finnhub
  - NewsAPI
  - GDELT
- Keep missing-key behavior clean and non-breaking.
- Add API-key status visibility for each provider.

### 7.6 Regional Query Data Support

- Improve region normalization for user questions.
- Support state names, abbreviations, and metro names where data allows.
- Add examples such as:
  - Arizona
  - AZ
  - Phoenix
  - Phoenix metro
- Return clear uncertainty when only national data is available.

### 7.7 Source Fallback Strategy

- Use local stored data first.
- Refresh official APIs when local data is missing or stale.
- Use approved live lookup/search where compliant and available.
- Explain which source path was used.

### 7.8 Phase 7 Validation And Docs

- Run parser and ingestion tests.
- Document configured, optional, and deferred sources.
- Add troubleshooting for API keys and source failures.

## Milestone Docs

- [Milestone 7.1: Source status audit](milestones/7.1-source-status-audit.md)
- [Milestone 7.2: Census parser completion](milestones/7.2-census-parser-completion.md)
- [Milestone 7.3: FHFA parser completion](milestones/7.3-fhfa-parser-completion.md)
- [Milestone 7.4: Freddie Mac PMMS parser completion](milestones/7.4-freddie-mac-pmms-parser-completion.md)
- [Milestone 7.5: Optional provider connectors](milestones/7.5-optional-provider-connectors.md)
- [Milestone 7.6: Regional query data support](milestones/7.6-regional-query-data-support.md)
- [Milestone 7.7: Source fallback strategy](milestones/7.7-source-fallback-strategy.md)
- [Milestone 7.8: Phase 7 validation and docs](milestones/7.8-phase-7-validation-and-docs.md)

## Definition Of Done

- Scaffolded source/parser statuses are resolved or explicitly deferred.
- Census, FHFA, and Freddie Mac paths are implemented or clearly documented if blocked by source access.
- Optional providers fail cleanly when keys are missing.
- The app has better regional data support.
- The agent can access a broader evidence base for Phase 8 flexible retrieval.
