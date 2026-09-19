# Implementation Phases

Last updated: 2026-09-05

This document tracks the full InvestorAgent implementation roadmap from planning through advanced features.

## Current Status

- Phase 1: Complete
- Phase 2: Complete
- Phase 3: Complete
- Phase 4: Complete
- Phase 5: Complete
- Phase 6: Complete

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

Status: Complete

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
- [Milestone 5.8: Proactive briefing suggestions](../phases/phase-5/milestones/5.8-proactive-briefing-suggestions.md).
- [Milestone 5.9: Scheduler hardening and automatic report runs](../phases/phase-5/milestones/5.9-scheduler-hardening-and-automatic-report-runs.md).
- [Milestone 5.10: Phase 5 validation and docs](../phases/phase-5/milestones/5.10-phase-5-validation-and-docs.md).

Planned milestones:

None.

## Phase 6: Simpler UI And Personalization

Status: Complete

Purpose: turn the working research system into a simpler, personalized user experience where the user mostly asks one natural-language question and the app figures out the rest.

User feedback driving this phase:

- The current screen has too much information visible at once.
- The user has to do too much manual work across Dashboard, Daily Briefing, Reports, Watchlist, Agent Chat, Sources, and Settings.
- Agent Chat is too restrictive because the user has to choose intent/domain and type tickers manually.
- The user should only need to type the question in the normal path.
- Intent, domain, tickers, companies, location, region, and report type should be auto-detected.
- Technical details like source health, ingestion runs, raw scheduler status, and citations should be available but not dominate the first screen.
- The product should feel like a personal intelligence desk, not an internal operations dashboard.

Deliverables:

- A simplified home screen centered on one primary question box.
- Auto-detected intent, domain, ticker/company, region, and report type from the user's question.
- Advanced controls hidden behind an optional panel instead of always visible.
- Personalization profile for default location, watchlist, topics, sectors, housing interests, and briefing preferences.
- Editable watchlist and saved preference management.
- Cleaner Daily Briefing, Reports, Watchlist, Housing/Macro, and Agent Chat views.
- A less cluttered dashboard that highlights:
  - today's briefing
  - suggested next actions
  - saved reports
  - important source/API status only when action is needed
- User-friendly source/API-key status with labels such as:
  - working
  - missing API key
  - parser not implemented
  - scaffolded only
  - skipped
  - stale
- Clearer empty states and next-step prompts.
- Fewer manual dropdowns in the main workflow.
- Tests for automatic query parsing, preference defaults, and simplified UI data contracts.

Completed milestones:

- [Milestone 6.1: UI information architecture cleanup](../phases/phase-6/milestones/6.1-ui-information-architecture-cleanup.md).
- [Milestone 6.2: Personalization profile](../phases/phase-6/milestones/6.2-personalization-profile.md).
- [Milestone 6.3: One-question primary workflow](../phases/phase-6/milestones/6.3-one-question-primary-workflow.md).
- [Milestone 6.4: Cleaner report and briefing views](../phases/phase-6/milestones/6.4-cleaner-report-and-briefing-views.md).
- [Milestone 6.5: Source/API status UX](../phases/phase-6/milestones/6.5-source-api-status-ux.md).
- [Milestone 6.6: Phase 6 validation and docs](../phases/phase-6/milestones/6.6-phase-6-validation-and-docs.md).

Not in scope:

- Major new external data connectors.
- Native desktop packaging.
- Broad live web search/retrieval.

Next phase:

- Phase 7: Source Expansion And Parser Completion.

## Phase 7: Source Expansion And Parser Completion

Status: Planned

Purpose: finish scaffolded API connectors/parsers and broaden credible source coverage so the app can answer more flexible data questions, including regional housing and macro questions.

User feedback driving this phase:

- Some API sources are still scaffolded and need real parsers.
- The app should retrieve information from multiple credible places so the user does not need to check many websites manually.
- Questions like "what are mortgage rates for AZ?" should work with local data when available and clear fallback behavior when local data is missing.
- The app needs broader official, market, company, housing, and news data before desktop packaging.

Deliverables:

- Finish Census Economic Indicators connector and parser.
- Finish FHFA House Price Index connector and parser.
- Finish Freddie Mac PMMS connector and parser.
- Add or complete optional API-key providers:
  - Alpha Vantage
  - Finnhub
  - NewsAPI
  - GDELT
- Add source-specific tests for parser behavior, skipped/missing-key handling, and normalized output.
- Improve regional data support for states/metros where available.
- Add source fallback logic:
  - local stored data first
  - official API refresh when stale or missing
  - approved live lookup/search path where compliant and available
- Add clearer source coverage metadata so the UI can explain why a question can or cannot be answered.
- Add regional housing/mortgage examples to tests and docs.

Not in scope:

- Native desktop packaging.
- Full autonomous agent planning.
- Paid/licensed data providers unless manually configured.

Detailed plan: [Phase 7](../phases/phase-7/README.md).

## Phase 8: Agent Framework Restructure And Web-First Research

Status: Planned

Purpose: restructure the multi-agent system, LLM orchestration, retrieval flow, and answer generation so the app behaves like a web-capable research assistant. The user should ask one question, the system should search credible live sources when appropriate, use direct APIs/local data as support and verification, then return a concise cited answer.

User feedback driving this phase:

- Agents should be able to infer what the user wants instead of requiring dropdowns.
- The current agent framework is too constrained by stored local data.
- Controlled live web research should be the main flexible-answer path for current, broad, local, or under-specified questions.
- Direct APIs and local stored data should remain important, but mainly as official measurements, structured context, cache, history, and verification.
- The user wants less typing and fewer clicks, with the app automatically selecting sources and agent workflows.
- The system should feel proactive and personalized to the user's situation.
- Final answers should be clean, natural-language, cited responses, not raw agent logs or dense source/debug summaries.

Deliverables:

- New planner/coordinator architecture for intent, entity, region, time-window, source, retrieval, and agent selection.
- Query understanding for locations, tickers, companies, sectors, topics, and time ranges.
- A Live Web Research Agent that can search approved credible sources as the primary flexible retrieval path, require citations, label live-web evidence clearly, and respect financial guardrails.
- Evidence fusion that combines web research, direct APIs, local observations/articles, saved reports, and source health.
- Multi-step workflows that can:
  - create a research plan
  - search the web
  - run targeted source/API lookup
  - inspect local/cached evidence
  - rank and reconcile evidence
  - run specialist agents
  - synthesize a final cited answer
- Automatic source selection based on query needs.
- Better uncertainty behavior when evidence is conflicting, unavailable, or too thin after web/API retrieval.
- Personalization-aware proactive briefings and report suggestions.
- Natural-language answers as the default output, with citations and structured details expandable.
- Guardrail checks that continue to prevent direct buy/sell/hold instructions.
- Tests and evaluation fixtures for flexible queries such as:
  - "What are mortgage rates in AZ?"
  - "What is happening with housing in Arizona right now?"
  - "What matters for my watchlist today?"
  - "How does the latest rate data affect housing?"
  - "What changed with Apple this week?"

Completed milestones:

- [Milestone 8.1: Agent architecture reset](../phases/phase-8/milestones/8.1-agent-architecture-reset.md).
- [Milestone 8.2: Query understanding and research planning](../phases/phase-8/milestones/8.2-query-understanding-and-research-planning.md).
- [Milestone 8.3: Controlled live web research](../phases/phase-8/milestones/8.3-controlled-live-web-research.md).

Not in scope:

- Native desktop packaging.
- Multi-user cloud deployment.

Detailed plan: [Phase 8](../phases/phase-8/README.md).

## Phase 9: Final UI, Prompting, And Product Polish

Status: Planned

Purpose: do a final product-quality pass after source coverage and agent flexibility are stronger, so the UI and prompts are polished around real working functionality rather than temporary data gaps.

User feedback driving this phase:

- The UI still does not feel simple or polished enough.
- The user is not fully happy with what the app returns yet.
- Some of the output quality issue is caused by missing data, scaffolded sources, incomplete parsers, and limited retrieval.
- The app should feel more personal, less cluttered, and less like a dashboard.
- Daily briefings should avoid feeling sparse or filled with empty sections once the data layer improves.
- Prompting should be tuned after the app has enough source coverage to answer richer questions.

Deliverables:

- Full UX review after Phase 7 source work and Phase 8 agent automation.
- Final Dashboard layout cleanup.
- Cleaner briefing and report presentation.
- Prompt improvements for daily briefings and natural-language answers.
- Better handling of no-data, sparse-data, stale-data, and uncertainty language.
- Navigation and workflow simplification before packaging.
- Final readiness check before desktop app work.

Not in scope:

- New source connector implementation.
- Major agent retrieval architecture changes.
- Desktop packaging.

Detailed plan: [Phase 9](../phases/phase-9/README.md).

## Phase 9.5: Product Differentiation Cleanup

Status: Complete

Purpose: bridge the gap between a working research app and an everyday-use personal intelligence product before desktop deployment.

User feedback driving this phase:

- The app should feel less like manually asking Codex or a generic chatbot.
- Preset topics should already show daily generated responses instead of acting like prompt buttons.
- The user should open the app and immediately see useful personalized intelligence.
- The app needs a simple setup/login/profile flow so user details and settings are captured cleanly.
- Responses should be easier to scan with Markdown-style headers, bold key terms, short bullets, and fewer walls of text.
- The product should become more unique through daily change tracking, signal/noise filtering, watch items, alerts, and future widgets.

Deliverables:

- Document the product differentiation north star and cleanup milestones.
- Create a simple first-time setup/profile flow.
- Turn preset cards into stored daily topic panels.
- Render cleaner Markdown answers with hidden evidence drawers.
- Add "what changed since yesterday/last week" and signal/noise labels.
- Add saved watch items and an alerts foundation.
- Document future add-ons such as menu bar status, desktop widgets, weekly exports, and monitor-style notifications.

Not in scope:

- Final macOS `.app` packaging.
- Portable Docker deployment.
- Multi-user cloud sync.

Detailed plan: [Phase 9.5](../phases/phase-9-5/README.md).

## Phase 9.6: Option M Visual Product Implementation

Status: Planned

Purpose: implement the approved Option M product direction before desktop deployment, making VerityDesk a visual daily intelligence app with an agent explanation layer.

User feedback driving this phase:

- Option M is the preferred direction because it is simpler, more futuristic, and more visual.
- Direct API/source data should power visuals, stats, and charts.
- Tavily and agents should power flexible questions and explanations.
- Home should stay visual and simple.
- Clicking visual modules should open deeper API/source stat views.
- The Daily Brief should be its own autogenerated markdown-style AI brief page.
- Agent Chat should include active chat and previous chats on the same page, similar to ChatGPT/Codex.
- Asking from Home should shift focus into Agent Chat.
- The app needs an official login and setup process.
- Settings should hold complexity, including sources, refresh controls, watch items, profile, and schedule.

Deliverables:

- Option M Home layout.
- Official login/setup flow.
- Home visual modules for Daily Read, Housing, Markets, Companies, and Macro.
- Visual module data API contract.
- Drill-down views with charts, key stats, source timestamps, and `Ask About This`.
- Dedicated Daily Brief page with markdown AI briefing.
- Agent Chat with active session memory and previous chats in the same view.
- Settings consolidation.
- Testing and local validation before desktop deployment.

Not in scope:

- macOS `.app` packaging.
- Portable Docker deployment.
- Cloud multi-user sync.

Detailed plan: [Phase 9.6](../phases/phase-9-6/README.md).

## Phase 10: Local Desktop App

Status: In progress

Purpose: package the local web app as a native-feeling macOS desktop app after the Option M visual product implementation is reliable.

Deliverables:

- Electron app shell for the first desktop packaging pass.
- macOS `.app` build.
- App name: VerityDesk.
- Local backend startup and shutdown behavior.
- Packaged database mode that does not require Docker Desktop or Postgres.app.
- Dev Postgres support preserved through `DATABASE_URL`.
- Local storage path handling for database, logs, and config.
- Automatic database migrations on packaged app startup.
- API key/config handling outside frontend code.
- Clean simple install/run/database documentation.

Milestones:

- [Milestone 10.1: Deployment architecture](../phases/phase-10/milestones/10.1-deployment-architecture.md).
- [Milestone 10.2: Desktop runtime shell](../phases/phase-10/milestones/10.2-desktop-runtime-shell.md).
- [Milestone 10.3: Packaged database mode](../phases/phase-10/milestones/10.3-packaged-database-mode.md).
- [Milestone 10.4: API key and local config handling](../phases/phase-10/milestones/10.4-api-key-and-local-config.md).
- [Milestone 10.5: Production builds](../phases/phase-10/milestones/10.5-production-builds.md).
- [Milestone 10.6: macOS app packaging](../phases/phase-10/milestones/10.6-macos-app-packaging.md).
- Milestone 10.7: End-to-end deployment test.
- Milestone 10.8: Clean simple documentation.

Detailed plan: [Phase 10](../phases/phase-10/README.md).

## Phase 11: Portable Deployment

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

## Phase 12: Quality, Safety, And Evaluation

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

## Phase 13: Advanced Features

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
