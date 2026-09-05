# Implementation Phases

Last updated: 2026-09-02

This document tracks the full InvestorAgent implementation roadmap from planning through advanced features.

## Current Status

- Phase 1: Complete
- Phase 2: Complete
- Phase 3: Complete
- Phase 4: Complete

## Phase 1: Research And Planning

Status: Complete

Purpose: define the product, sources, architecture, compliance posture, and build direction before coding.

Deliverables:

- Product vision.
- Financial disclaimer and investment-output guardrails.
- V1 news-domain taxonomy.
- Recommended architecture.
- Initial source catalog.
- Compliance rules for APIs, RSS, scraping, and source storage.
- Multi-agent architecture.
- Agent input/output contracts.
- Data model sketch.
- UI screen spec.
- Report templates.
- Phase 2 build scope.

## Phase 2: Application Scaffold

Status: Complete

Purpose: build the first runnable local app skeleton.

Deliverables:

- `frontend/` Next.js app with TypeScript.
- `backend/` FastAPI app.
- Modular FastAPI API structure.
- SQLite database setup.
- SQLAlchemy models.
- Alembic migrations.
- Static source catalog configuration.
- Backend endpoints:
  - `GET /health`
  - `GET /sources`
  - `GET /reports`
  - `GET /settings`
  - `POST /settings`
  - `POST /agents/query`
- Placeholder agent contracts.
- Financial disclaimer and basic guardrail module.
- Frontend pages:
  - Dashboard
  - Daily Briefing
  - Sources
  - Watchlist
  - Agent Chat
  - Settings
- Docker Compose local run path.
- README local setup instructions.

Completed milestones:

- [Milestone 2.1: Repo and tooling scaffold](../phases/phase-2/milestones/2.1-repo-and-tooling-scaffold.md).
- [Milestone 2.2: Backend foundation](../phases/phase-2/milestones/2.2-backend-foundation.md).
- [Milestone 2.3: Database foundation](../phases/phase-2/milestones/2.3-database-foundation.md).
- [Milestone 2.4: Source catalog foundation](../phases/phase-2/milestones/2.4-source-catalog-foundation.md).
- [Milestone 2.5: Agent and guardrail contracts](../phases/phase-2/milestones/2.5-agent-and-guardrail-contracts.md).
- [Milestone 2.6: Frontend shell](../phases/phase-2/milestones/2.6-frontend-shell.md).

Next phase:

- Phase 3: Data ingestion.

Phase 2 does not need full live ingestion or final agent intelligence.

## Phase 3: Data Ingestion

Status: Complete

Purpose: connect the app to direct sources and begin collecting real data.

Deliverables:

- RSS ingestion pipeline.
- API ingestion pipeline.
- Source scheduler.
- Article/data normalization.
- Deduplication.
- Source health tracking.
- Storage policies by source.
- Initial live connectors:
  - BBC RSS
  - SEC data APIs
  - SEC EDGAR RSS
  - FRED
  - U.S. Census Economic Indicators
  - FHFA HPI
  - Freddie Mac PMMS
- Optional API-key connectors:
  - Alpha Vantage
  - Finnhub
  - NewsAPI
  - GDELT

Completed milestones:

- [Milestone 3.1: Ingestion data model](../phases/phase-3/milestones/3.1-ingestion-data-model.md).
- [Milestone 3.2: RSS ingestion foundation](../phases/phase-3/milestones/3.2-rss-ingestion-foundation.md).
- [Milestone 3.3: Official API ingestion foundation](../phases/phase-3/milestones/3.3-official-api-ingestion-foundation.md).
- [Milestone 3.4: Source scheduler](../phases/phase-3/milestones/3.4-source-scheduler.md).
- [Milestone 3.5: Source health and freshness API](../phases/phase-3/milestones/3.5-source-health-and-freshness-api.md).
- [Milestone 3.6: Frontend ingestion visibility](../phases/phase-3/milestones/3.6-frontend-ingestion-visibility.md).
- [Milestone 3.7: Phase 3 validation and docs](../phases/phase-3/milestones/3.7-phase-3-validation-and-docs.md).

Next phase:

- Phase 4: Agent Framework.

## Phase 4: Agent Framework

Status: Complete

Purpose: add the multi-agent research system.

Deliverables:

- `CoordinatorAgent`
- `NewsDigestAgent`
- `CompanyAgent`
- `MarketAgent`
- `MacroAgent`
- `HousingAgent`
- `CitationAgent`
- `RiskGuardrailAgent`
- Agent run logging.
- Agent routing based on user intent, domains, tickers, companies, and regions.
- Structured agent outputs with citations and confidence levels.
- Natural-language final synthesis layered over structured specialist findings.

Completed milestones:

- [Milestone 4.1: Agent runtime foundation](../phases/phase-4/milestones/4.1-agent-runtime-foundation.md).
- [Milestone 4.2: Research data access layer](../phases/phase-4/milestones/4.2-research-data-access-layer.md).
- [Milestone 4.3: Domain agent implementations](../phases/phase-4/milestones/4.3-domain-agent-implementations.md).
- [Milestone 4.4: Coordinator routing and synthesis](../phases/phase-4/milestones/4.4-coordinator-routing-and-synthesis.md).
- [Milestone 4.5: Citations and guardrail enforcement](../phases/phase-4/milestones/4.5-citations-and-guardrails.md).
- [Milestone 4.6: Agent API and UI integration](../phases/phase-4/milestones/4.6-agent-api-and-ui-integration.md).
- [Milestone 4.7: Phase 4 validation and docs](../phases/phase-4/milestones/4.7-phase-4-validation-and-docs.md).

Next phase:

- Phase 5: Research Output System.

## Phase 5: Research Output System

Status: In Progress

Purpose: generate high-quality cited reports from collected data and agent outputs.

Deliverables:

- Daily briefing generation.
- Company research report generation.
- Market strategy report generation.
- Housing and macro report generation.
- Report persistence.
- Citation panel support.
- Scenario framing.
- Required risks and uncertainty sections.
- Required disclaimer in investment-oriented reports.
- Proactive daily context and suggested follow-up questions based on saved preferences, watchlists, and recent ingested data.
- Economic observation cleanup:
  - Friendly labels for FRED series IDs such as `UNRATE`, `FEDFUNDS`, and `MORTGAGE30US`.
  - Grouped economic observations so repeated FRED records do not dominate the UI or reports.
  - Clear separation between article/news items and structured economic data points.
- Source expansion:
  - Finish Census Economic Indicators connector.
  - Finish FHFA House Price Index connector.
  - Finish Freddie Mac PMMS connector.
  - Add optional API-key connectors for Alpha Vantage, Finnhub, NewsAPI, and GDELT.
- Scheduler hardening:
  - Persist scheduler settings.
  - Enable true automatic daily background ingestion.

Completed milestones:

- [Milestone 5.1: Report data model and API contracts](../phases/phase-5/milestones/5.1-report-data-model-and-api-contracts.md).
- [Milestone 5.2: Evidence cleanup and source data quality](../phases/phase-5/milestones/5.2-evidence-cleanup-and-source-data-quality.md).
- [Milestone 5.3: Daily briefing generator](../phases/phase-5/milestones/5.3-daily-briefing-generator.md).
- [Milestone 5.4: Company research report generator](../phases/phase-5/milestones/5.4-company-research-report-generator.md).
- [Milestone 5.5: Market strategy and scenario reports](../phases/phase-5/milestones/5.5-market-strategy-and-scenario-reports.md).
- [Milestone 5.6: Housing and macro reports](../phases/phase-5/milestones/5.6-housing-and-macro-reports.md).
- [Milestone 5.7: Report persistence and citation panels](../phases/phase-5/milestones/5.7-report-persistence-and-citation-panels.md).

Planned milestones:

- [Milestone 5.8: Proactive briefing suggestions](../phases/phase-5/milestones/5.8-proactive-briefing-suggestions.md).
- [Milestone 5.9: Scheduler hardening and automatic report runs](../phases/phase-5/milestones/5.9-scheduler-hardening-and-automatic-report-runs.md).
- [Milestone 5.10: Phase 5 validation and docs](../phases/phase-5/milestones/5.10-phase-5-validation-and-docs.md).

## Phase 6: Full UI Dashboard

Status: Planned

Purpose: turn the scaffold into a complete user-facing research workspace.

Deliverables:

- Polished dashboard.
- Full daily briefing view.
- Watchlist management.
- Company research view.
- Macro and housing view.
- Source manager.
- Saved reports.
- Agent chat workspace.
- Settings and API-key status.
- Domain filters for the ten news categories.
- User-friendly source status explanations for skipped, not configured, placeholder, and missing API-key states.
- More automated agent experience: saved preferences, watchlist-aware defaults, proactive briefings, and suggested questions so users do not always need to start from a blank query box.

## Phase 7: Local Desktop App

Status: Planned

Purpose: package the local web app as a native-feeling macOS desktop app.

Deliverables:

- Tauri app shell.
- macOS `.app` build.
- macOS `.dmg` build.
- App icon.
- Local backend startup behavior.
- Desktop menu basics.
- Local storage path handling.

## Phase 8: Portable Deployment

Status: Planned

Purpose: make the app easy for someone else to run on their own system.

Deliverables:

- Docker Compose production-like local setup.
- `.env.example`.
- Seed source catalog.
- Local database initialization.
- One-command startup path.
- Clear install/run documentation.
- Basic troubleshooting notes.

## Phase 9: Quality, Safety, And Evaluation

Status: Planned

Purpose: make the system reliable, testable, and safe for research use.

Deliverables:

- Backend tests.
- Frontend smoke tests.
- Ingestion tests.
- Source validation tests.
- Citation coverage checks.
- Financial guardrail tests.
- Agent output evaluation fixtures.
- Error logging.
- Failed-source monitoring.
- Staleness checks.

## Phase 10: Advanced Features

Status: Planned

Purpose: add higher-value features after the core product works.

Deliverables:

- Alerts.
- Earnings calendar.
- SEC filing summaries.
- Portfolio-context research mode.
- Sector comparison.
- Regional housing comparison.
- Report export to PDF.
- Email or local notification digest.
- Multi-user or cloud-ready mode if needed.
- More licensed data providers.

## Build Principle

Each phase should produce a usable increment. The project should avoid building complex agents or scraping logic before the app scaffold, data model, source catalog, and guardrail foundations are in place.
