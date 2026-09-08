# InvestorAgent

InvestorAgent is a local-first market intelligence application concept that combines credible news collection, multi-agent research workflows, and an interactive UI for daily financial context.

The goal is to help users understand what is happening across world news, company news, markets, macroeconomics, and housing, then turn that information into cited research summaries, watchlist ideas, and scenario-based investing context.

> This project is for research and educational purposes only. It does not provide financial advice, investment recommendations, or instructions to buy or sell securities. Users should do their own research and consult a licensed financial advisor before making investment decisions.

## Product Vision

InvestorAgent should feel like a personal market intelligence terminal:

- Daily digest of major world, business, market, macro, and housing news.
- Company and ticker-focused research summaries.
- Market strategy context with bullish factors, bearish factors, risks, and watchlist signals.
- Source-backed answers with citations, timestamps, and clear separation between facts and analysis.
- Local desktop app experience for macOS, with a portable version others can run on their own machine.

## News Domains

InvestorAgent v1 is organized around ten news domains:

1. World and Geopolitics
2. U.S. Economy and Policy
3. Markets and Rates
4. Companies and Earnings
5. Housing and Real Estate
6. Commodities and Energy
7. Technology and AI
8. Banking and Credit
9. Consumer and Labor
10. Regulation and Legal

## Core Capabilities

- Collect news and data from credible sources using APIs, RSS feeds, and compliant scraping where appropriate.
- Run scheduled daily collection jobs.
- Deduplicate, normalize, and store articles, source metadata, tickers, sectors, and macro indicators.
- Analyze user questions through specialized agents.
- Generate daily briefings and focused reports.
- Show source links for claims and preserve retrieved timestamps.
- Apply financial guardrails to strategy-oriented outputs.

## Agent Framework

The system is designed around a coordinator agent that routes user requests to specialized agents.

Potential agents:

- `CoordinatorAgent`: understands the user request and decides which agents should run.
- `WorldNewsAgent`: summarizes major geopolitical and global economic developments.
- `CompanyNewsAgent`: tracks company-specific events, earnings, management changes, and product news.
- `MarketNewsAgent`: watches equity markets, sectors, commodities, bonds, currencies, and volatility.
- `MacroAgent`: follows inflation, jobs, rates, Fed commentary, GDP, and other macro indicators.
- `HousingMarketAgent`: tracks housing supply, mortgage rates, affordability, prices, and regional trends.
- `StrategyAgent`: converts research into scenario-based market context and watchlist themes.
- `CitationAgent`: verifies claims, attaches sources, and flags unsupported conclusions.
- `RiskAgent`: checks for missing caveats, uncertainty, and financial-advice wording.

## Financial Guardrails

InvestorAgent should never directly tell a user to buy, sell, or hold a security.

Instead of:

```text
Buy NVDA.
```

The app should say:

```text
NVDA may be worth monitoring if earnings revisions, AI infrastructure demand, and margin trends remain strong. Key risks include valuation compression, export restrictions, and increased competition. This is not financial advice.
```

Every investment-oriented answer should include:

- Clear disclaimer.
- Bullish factors.
- Bearish factors.
- Key risks.
- Time horizon assumptions.
- Source citations.
- "Not a recommendation" framing.

## App Architecture

Recommended architecture:

- Frontend: Next.js with TypeScript.
- Backend API: FastAPI.
- Agent orchestration: Python-based workflow, such as LangGraph-style routing.
- Storage: SQLite with SQLAlchemy and Alembic for local-first development, with a path to Postgres later.
- Collection: RSS and official APIs first, Playwright/browser scraping only where compliant and necessary.
- Scheduling: local background jobs for daily updates.
- LLM provider: OpenAI API first, behind a provider abstraction.
- Packaging: Tauri for a native desktop app later, plus Docker Compose for portable self-hosting.

## Deployment Targets

InvestorAgent should support two main deployment paths:

1. Local desktop app
   - Installable macOS app.
   - Opens like a normal desktop application.
   - Uses the same local backend and storage.

2. Portable local web app
   - Runs through Docker or a simple local command.
   - Opens in a browser.
   - Can be shared with someone else to run on their own system.

Deployment timing:

- Phase 9 is the final UI, prompting, and product polish pass after source and agent functionality are stronger.
- Phase 10 packages the app as a local macOS desktop app.
- Phase 11 focuses on portable deployment for other systems.

## Source Principles

The project should prioritize reputable and compliant sources:

- Official company investor relations pages.
- SEC filings and earnings materials.
- Central bank and government economic data.
- Trusted financial and business news outlets.
- Housing and mortgage market data providers.
- RSS feeds and official APIs where available.

The system should respect source terms, paywalls, and `robots.txt`.

## Roadmap

- Define the initial source catalog.
- Build the local database schema.
- Implement daily ingestion jobs.
- Add article deduplication and source metadata.
- Build the first set of specialist agents.
- Create a dashboard UI with daily digest, watchlist, and chat/research modes.
- Add guardrail checks and citation enforcement.
- Package the app for local desktop use.
- Add Docker support for portable deployment.

## Status

Phases 1-6 are complete. Next planned work is Phase 7: source expansion and parser completion.

## Local Development

Phase 2 uses a split local app:

- `frontend/`: Next.js with TypeScript.
- `backend/`: FastAPI in Python.

Runtime requirements:

- Node.js `>=20.9.0`
- Python `>=3.11`

This repo supports a project-local Node install at `.runtime/node-v22.23.2-darwin-arm64`. The `.runtime/` directory is ignored by git because it is machine-local.

Install the project-local Node runtime:

```bash
make node-install
```

Use it in your shell with:

```bash
export PATH="$PWD/.runtime/node-v22.23.2-darwin-arm64/bin:$PATH"
node --version
npm --version
```

Copy the example environment file before running local services:

```bash
cp .env.example .env
```

Start the local app with one command:

```bash
make app-dev
```

This applies database migrations, starts the backend at `http://localhost:8000`, and starts the frontend at `http://localhost:3000`. Press `Ctrl+C` in that terminal to stop both services.

For Phase 8 live web research, add `TAVILY_API_KEY` to `.env`. Without it, the app keeps running and live web search returns a clean missing-key status.

In the app:

- Use **Dashboard** to ask one question, open the latest briefing, view saved reports, and review suggested next steps.
- Use **Daily Briefing** to generate and read a saved briefing from current evidence.
- Use **Reports** to reopen saved reports after restart, refresh reports, archive reports, delete reports, and inspect citations/details when needed.
- Use **Sources** to review source/API status, run manual ingestion, inspect latest retrieved items, and see recent ingestion runs.
- Use **Watchlist** to generate company research.
- Use **Agent Chat** for custom research questions with automatic context detection and optional Advanced controls.
- Use **Settings** to save personalization, enable daily automation, set the scheduled time, choose ingestion mode, and optionally generate an automatic daily briefing after ingestion.

Daily automation only runs while the local backend is open. The schedule is saved in the local database and the startup command applies migrations automatically.

Run the backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -e backend[dev]
make backend-dev
```

Run backend checks and migrations from the repo root:

```bash
make backend-test
make backend-lint
make db-upgrade
```

Run the configured RSS ingestion sources:

```bash
make rss-ingest
```

Run the configured official API and dataset ingestion sources:

```bash
make official-api-ingest
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

From the repo root, the Makefile automatically uses the project-local Node runtime:

```bash
make frontend-dev
make frontend-build
make frontend-typecheck
```

Or run both with Docker Compose:

```bash
docker compose up --build
```

Local URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- Source catalog: `http://localhost:8000/api/v1/sources`
- Agent query: `POST http://localhost:8000/api/v1/agents/query`
- Ingestion run: `POST http://localhost:8000/api/v1/ingestion/run`
- Ingestion health: `http://localhost:8000/api/v1/ingestion/health`
- Latest ingested items: `http://localhost:8000/api/v1/ingestion/latest-items`
- Scheduler status: `http://localhost:8000/api/v1/ingestion/schedule`
- Saved reports: `http://localhost:8000/api/v1/reports`
- Proactive suggestions: `http://localhost:8000/api/v1/suggestions/proactive`

## Planning Docs

- [Documentation Index](docs/README.md)
- [Implementation Phases](docs/roadmap/implementation-phases.md)
- [Phase 1](docs/phases/phase-1/README.md)
- [Phase 2](docs/phases/phase-2/README.md)
- [Phase 3](docs/phases/phase-3/README.md)
- [Phase 4](docs/phases/phase-4/README.md)
- [Phase 5](docs/phases/phase-5/README.md)
