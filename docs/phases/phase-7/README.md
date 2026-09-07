# Phase 7: Source Expansion And Parser Completion

Status: Complete

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

Status: Complete

- Add or complete optional providers:
  - Alpha Vantage
  - Finnhub
  - NewsAPI
  - GDELT
- Keep missing-key behavior clean and non-breaking.
- Add API-key status visibility for each provider.

### 7.6 Regional Query Data Support

Status: Complete

- Improve region normalization for user questions.
- Support state names, abbreviations, and metro names where data allows.
- Add examples such as:
  - Arizona
  - AZ
  - Phoenix
  - Phoenix metro
- Return clear uncertainty when only national data is available.

### 7.7 Source Fallback Strategy

Status: Complete

- Use local stored data first.
- Refresh official APIs when local data is missing or stale.
- Use approved live lookup/search where compliant and available.
- Explain which source path was used.

### 7.8 Phase 7 Validation And Docs

Status: Complete

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

## Phase 7 Closeout

Completed source work:

- Census EITS parser for selected economic indicator datasets.
- FHFA HPI parser for U.S./Census-region, state, and metro house-price data.
- Freddie Mac PMMS parser for national weekly mortgage-rate data.
- Alpha Vantage optional connector for news sentiment, market movers, and quote snapshots.
- Finnhub optional connector for company news and quote snapshots.
- NewsAPI optional connector for article discovery and U.S. top headlines.
- GDELT no-key connector for broad global article discovery.
- Regional query support for state aliases and starter metro aliases.
- Source fallback summaries for agents and LLM prompts.

Manual keys currently expected:

- `FRED_API_KEY`
- `CENSUS_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FINNHUB_API_KEY`
- `NEWSAPI_KEY`

No manual key expected:

- SEC data APIs
- BBC RSS
- SEC EDGAR RSS
- FHFA HPI
- Freddie Mac PMMS
- GDELT DOC search

Validation on September 7, 2026:

- `make backend-test`: 153 passed.
- `make backend-lint`: passed.
- `make frontend-typecheck`: passed.
- `make frontend-build`: passed.
- `git diff --check`: passed.

Phase 8 should now focus on agent automation, controlled live web research, personalization-aware retrieval, and reducing manual UI work.

Important user expectation for Phase 8 and later:

- The app should feel like one clean daily intelligence desk, not a collection of source tables and manual filters.
- The user should mostly type only the question; the app should infer sources, agents, regions, tickers, and time windows.
- Agent responses should be concise, readable, and useful for a non-technical user.
- The agent framework should not be limited to only the already-ingested database when evidence is missing. It should use controlled, cited live web research similar to how Codex can look things up, while preserving credibility, attribution, rate limits, and financial-advice guardrails.
- UI cleanup after functionality lands should remove dense lists from the main path and keep detailed source/debug information behind secondary views.
