# Phase 1 Research

Last updated: 2026-09-01

InvestorAgent is a local-first market intelligence app that collects credible news and data, routes user questions through specialized agents, and produces cited research summaries with financial-safety guardrails.

This document captures the Phase 1 research needed before implementation.

## Phase 1 Goals

- Define the MVP product scope.
- Identify credible source categories and initial data providers.
- Establish compliance rules for scraping, APIs, feeds, and source storage.
- Define the first multi-agent architecture.
- Define output guardrails for investing-related responses.
- Choose a practical deployment direction for local desktop and portable use.

## Final Phase 1 Decisions

These are the recommended v1 decisions for Phase 2 implementation:

- Frontend: Next.js with TypeScript.
- Backend: FastAPI in Python.
- Local database: SQLite.
- ORM and migrations: SQLAlchemy and Alembic.
- Agent runtime: Python service with explicit agent contracts.
- LLM provider: OpenAI API first, behind a provider abstraction.
- Ingestion strategy: APIs and RSS feeds first.
- Scraping strategy: compliant lightweight extraction only when allowed by terms and `robots.txt`.
- Scheduler: APScheduler or equivalent local background job runner.
- Portable deployment: Docker Compose.
- Desktop packaging: Tauri after the web app and backend are working.
- Market/news data policy: use official/free sources first and support user-provided API keys for paid providers.
- Financial safety policy: research and education only, never direct personalized buy/sell/hold recommendations.

## MVP User Modes

The first version should support five user workflows:

1. Daily briefing
   - "What happened today that matters?"
   - Covers world news, business news, markets, macro, and housing.

2. Company research
   - "What is going on with Apple?"
   - Pulls company news, SEC filings, price context, earnings/calendar data, and cited summaries.

3. Market research
   - "What is moving markets today?"
   - Covers indexes, rates, commodities, sector themes, and risk sentiment.

4. Housing and macro research
   - "What is happening in housing and rates?"
   - Covers mortgage rates, home prices, sales, supply, affordability, inflation, jobs, Fed, and GDP.

5. Agent chat
   - User asks a natural-language question.
   - Coordinator decides which agents and sources are required.

## News Domain Taxonomy

InvestorAgent v1 should organize sources, articles, agents, filters, and daily briefings around ten primary news domains:

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

Articles and reports can belong to multiple domains. Example mappings:

- Fed rate decision: Markets and Rates, U.S. Economy and Policy.
- Apple earnings: Companies and Earnings, Technology and AI.
- Oil supply shock: Commodities and Energy, World and Geopolitics.
- Mortgage rates increase: Housing and Real Estate, Markets and Rates.
- DOJ antitrust case: Regulation and Legal, Companies and Earnings.

This taxonomy should drive:

- Source catalog labels.
- Database article tags.
- Agent routing.
- Dashboard sections.
- Daily briefing structure.
- User-facing filters.

## Source Strategy

The system should use sources in this order:

1. Official APIs and datasets.
2. Official RSS feeds and publisher APIs.
3. Licensed data APIs.
4. Compliant lightweight page extraction, only when allowed by terms and robots rules.

The app should avoid paywall bypassing, credential sharing, bulk copying of restricted publisher content, and building a full-text database from sources whose terms prohibit automated harvesting.

## V1 Source Catalog

The v1 source catalog should start small and reliable. Each source below should be represented in configuration with source name, access method, domain tags, auth requirements, update cadence, storage rules, and citation requirements.

| Source | Domains | Access | Auth | V1 Use |
| --- | --- | --- | --- | --- |
| BBC News RSS | World and Geopolitics, U.S. Economy and Policy, Companies and Earnings | Official RSS | No | Daily world/business headlines and summaries |
| SEC data APIs | Companies and Earnings, Regulation and Legal | Official API | No key, clear user agent required | Company submissions, XBRL facts, filing history |
| SEC EDGAR RSS | Companies and Earnings, Regulation and Legal | Official RSS | No | Recent structured filings and filing alerts |
| FRED API | U.S. Economy and Policy, Markets and Rates, Banking and Credit, Housing and Real Estate | Official API | API key recommended/required by endpoint policy | Macro series, rates, inflation, labor, credit spreads |
| U.S. Census Economic Indicators | U.S. Economy and Policy, Housing and Real Estate, Consumer and Labor | Official API | API key required | Housing construction, new home sales, trade, retail, construction spending |
| FHFA HPI | Housing and Real Estate | Official datasets | No | House price indexes across national, state, metro, ZIP, and tract levels |
| Freddie Mac PMMS | Housing and Real Estate, Markets and Rates | Official webpage/download | No | Weekly mortgage rate averages |
| Company investor relations pages | Companies and Earnings | Official company pages/RSS when available | No, unless company-specific | Press releases, earnings dates, shareholder letters, presentations |
| Alpha Vantage | Markets and Rates, Companies and Earnings, Commodities and Energy | Licensed/free-tier API | User API key | Optional stock, fundamental, economic, and news/sentiment data |
| Finnhub | Companies and Earnings, Markets and Rates | Licensed/free-tier API | User API key | Optional company news, quotes, sentiment |
| NewsAPI | World and Geopolitics, Technology and AI, Regulation and Legal, Companies and Earnings | Licensed/free-tier API | User API key | Optional article discovery and metadata, not full-content storage |
| GDELT Cloud | World and Geopolitics, Regulation and Legal, Commodities and Energy | API | API key depending on endpoint | Optional global story/event discovery |

V1 should not depend on AP, Reuters, NAR full data, Polygon, or Nasdaq Data Link unless the user supplies licensed credentials or the project explicitly confirms acceptable usage.

## Initial Source Catalog

### World And Business News

Recommended MVP sources:

- BBC RSS feeds for world/business headlines and summaries.
- AP Media API if a licensed API key is available.
- Reuters Connect RSS if a licensed Reuters Connect account is available.
- NewsAPI as a discovery layer for publisher URLs and metadata.
- GDELT Cloud as a broad event/story discovery source.

Notes:

- BBC exposes RSS-style syndication feeds and feed documentation.
- AP's Media API is licensed and key-based; it supports feed retrieval but content access depends on contract terms.
- Reuters RSS delivery appears to be authenticated through Reuters Connect.
- NewsAPI returns article metadata and truncated content, so the app should use it primarily for discovery, not as a full article store.
- GDELT is useful for global trend/event discovery but should not be treated as a final credibility authority by itself.

### Company And Filing Data

Recommended MVP sources:

- SEC `data.sec.gov` APIs for company submissions and XBRL company facts.
- SEC EDGAR RSS feeds for recent filings.
- Company investor relations RSS/news pages where available.
- Finnhub company news for North American companies if an API key is available.
- Alpha Vantage fundamentals, earnings, and news/sentiment if an API key is available.

Notes:

- SEC APIs are public and JSON-based, but automated access must comply with SEC policies and use respectful request behavior.
- SEC structured disclosure RSS feeds are updated every ten minutes during weekday EDGAR operating hours.
- Company investor relations pages are strong primary sources for press releases, earnings decks, transcripts, and corporate events.

### Market Data

Recommended MVP sources:

- Alpha Vantage for price time series, fundamentals, economic indicators, and news/sentiment.
- Nasdaq Data Link for professional real-time, delayed, historical, and alternative datasets where licensed.
- Polygon.io for market data where a subscription/API key is available.
- Finnhub for quotes, company news, and sentiment where an API key is available.

Notes:

- Market data licensing matters. The app should treat real-time/delayed exchange data as a licensed data product, not something to scrape from finance websites.
- The MVP can start with delayed/end-of-day data and source links, then support premium providers through user-provided API keys.

### Macro Data

Recommended MVP sources:

- FRED API for U.S. macroeconomic time series.
- BLS Public Data API for employment, CPI, PPI, wages, and labor statistics.
- U.S. Census API for economic indicators, construction, retail, trade, and housing-related time series.
- BEA API later for GDP, income, and national accounts.

Notes:

- FRED supports REST access and JSON/XML responses.
- Census Economic Indicators API includes housing-related datasets such as new residential construction and new home sales.
- BLS and Census often need series/dataset identifiers, so the project should maintain a curated indicator catalog.

### Housing Market Data

Recommended MVP sources:

- FHFA House Price Index datasets for national, state, metro, county, ZIP, and tract-level house price indexes.
- Freddie Mac PMMS for weekly mortgage rates.
- U.S. Census Economic Indicators for new residential construction, new home sales, housing vacancies, and construction spending.
- NAR existing-home sales releases as a referenced source, subject to reproduction restrictions.
- Redfin Data Center downloads for market tracker data if terms and intended use are acceptable.

Notes:

- FHFA HPI is public and available in CSV/JSON/XML-style dataset formats.
- Freddie Mac PMMS is a strong source for weekly mortgage rates.
- NAR publishes useful existing-home sales summaries but restricts reproduction, storage, and redistribution of data for non-members without consent; use carefully.
- Redfin provides broad downloadable housing datasets, but the app should verify and store acceptable use terms before using them in a distributed product.

## Compliance And Data Use Rules

### Scraping Rules

- Check `robots.txt` before crawling a site.
- Follow the Robots Exclusion Protocol.
- Respect publisher terms of service.
- Prefer feed/API access over scraping article pages.
- Do not bypass paywalls, login walls, CAPTCHAs, anti-bot systems, or geographic restrictions.
- Rate limit requests per domain.
- Use a clear `User-Agent` identifying the app and contact email.
- Cache source metadata and excerpts sparingly.
- Store links, titles, source names, published dates, retrieved dates, and summaries instead of full copyrighted article bodies when rights are unclear.

### Citation Rules

Every generated report should include:

- Source title.
- Publisher/source name.
- URL.
- Published timestamp when available.
- Retrieved timestamp.
- Data vintage where applicable.
- Which claims came from which source.

### Source Reliability Rules

Each source should have metadata:

- Category.
- News domain taxonomy tags.
- Type: official API, official RSS, licensed API, webpage, dataset.
- Geographic scope.
- Update cadence.
- Access method.
- Requires API key.
- Requires paid license.
- Allows article text storage.
- Allows redistribution.
- Known restrictions.
- Confidence level.

## Financial Guardrails

The app should not provide personalized financial advice or direct buy/sell/hold instructions.

Required disclaimer:

```text
This is not financial advice. The information shown is for research and educational purposes only. Investing involves risk. Do your own research and consider consulting a licensed financial advisor before making investment decisions.
```

Investment-oriented answers should use research framing:

- "May be worth monitoring..."
- "A possible watchlist signal is..."
- "A bullish scenario would require..."
- "A bearish scenario would be..."
- "Key risks include..."
- "This is not a recommendation to buy, sell, or hold."

Investment-oriented answers should avoid:

- "Buy this."
- "Sell this."
- "You should invest in..."
- "Guaranteed return."
- "Risk-free."
- Personalized instructions based on a user's portfolio, finances, taxes, or risk tolerance unless the product is redesigned as a regulated advisory product.

If the app outputs price targets, it should require:

- Valuation method.
- Time horizon.
- Assumptions.
- Downside scenario.
- Risk factors.
- Supporting sources.
- Explicit "not a recommendation" framing.

## Agent Architecture

### MVP Agents

- `CoordinatorAgent`
  - Classifies the user request.
  - Selects agents and source categories.
  - Sets output format and safety level.

- `NewsDigestAgent`
  - Builds daily global/business news briefing.
  - Clusters related articles.
  - Separates confirmed facts from developing stories.

- `CompanyAgent`
  - Handles ticker/company questions.
  - Uses company news, SEC filings, fundamentals, press releases, and market data.

- `MarketAgent`
  - Handles equity index, sector, rates, commodity, and volatility context.
  - Summarizes what moved and why.

- `MacroAgent`
  - Handles inflation, labor, GDP, rates, Fed, and economic calendar questions.

- `HousingAgent`
  - Handles mortgage rates, home prices, sales, inventory, supply, affordability, and regional housing trends.

- `CitationAgent`
  - Ensures each material claim has at least one citation.
  - Flags unsupported or stale claims.

- `RiskGuardrailAgent`
  - Checks for direct financial advice, exaggerated claims, missing risk language, and unsupported forecasts.

### Agent Flow

```text
User Request
  -> CoordinatorAgent
  -> Source Retrieval
  -> Specialist Agents
  -> CitationAgent
  -> RiskGuardrailAgent
  -> Final Report
```

## Agent Contracts

Each agent should use structured inputs and outputs so reports are auditable and testable.

### Shared Agent Input

- `request_id`
- `user_query`
- `intent`
- `domains`
- `tickers`
- `companies`
- `regions`
- `time_window`
- `source_ids`
- `safety_level`

### Shared Agent Output

- `summary`
- `claims`
- `citations`
- `confidence`
- `risks`
- `follow_up_questions`
- `requires_guardrail_review`

### Claim Object

- `claim`
- `claim_type`: fact, interpretation, forecast, risk, scenario.
- `source_ids`
- `confidence`
- `as_of`

## Data Model Sketch

Phase 2 should implement these entities first:

### `sources`

- `id`
- `name`
- `base_url`
- `source_type`
- `domains`
- `access_method`
- `requires_api_key`
- `requires_license`
- `allows_full_text_storage`
- `allows_redistribution`
- `robots_policy_checked_at`
- `terms_checked_at`
- `update_cadence`
- `reliability_tier`
- `enabled`
- `notes`

### `articles`

- `id`
- `source_id`
- `title`
- `url`
- `canonical_url`
- `publisher`
- `author`
- `published_at`
- `retrieved_at`
- `summary`
- `excerpt`
- `domains`
- `tickers`
- `companies`
- `regions`
- `content_hash`
- `dedupe_group_id`
- `storage_policy`

### `economic_observations`

- `id`
- `source_id`
- `series_id`
- `series_name`
- `value`
- `unit`
- `period`
- `released_at`
- `retrieved_at`
- `vintage`
- `region`

### `companies`

- `id`
- `name`
- `ticker`
- `exchange`
- `cik`
- `sector`
- `industry`
- `website`
- `investor_relations_url`

### `reports`

- `id`
- `report_type`
- `title`
- `summary`
- `body`
- `domains`
- `tickers`
- `companies`
- `created_at`
- `as_of`
- `disclaimer_version`
- `guardrail_status`

### `citations`

- `id`
- `report_id`
- `article_id`
- `source_id`
- `url`
- `title`
- `publisher`
- `published_at`
- `retrieved_at`
- `supports_claim`

### `agent_runs`

- `id`
- `request_id`
- `agent_name`
- `input`
- `output`
- `status`
- `started_at`
- `completed_at`
- `error`

### `user_settings`

- `id`
- `watchlist_tickers`
- `preferred_regions`
- `enabled_sources`
- `daily_briefing_time`
- `llm_provider`
- `api_key_status`
- `disclaimer_acknowledged_at`

## Recommended MVP Outputs

### Daily Briefing

- Executive summary.
- World and geopolitics.
- U.S. economy and policy.
- Markets and rates.
- Companies and earnings.
- Housing and real estate.
- Commodities and energy.
- Technology and AI.
- Banking and credit.
- Consumer and labor.
- Regulation and legal.
- Watchlist themes.
- Risks and uncertainties.
- Sources.
- Disclaimer.

### Company Research

- Company snapshot.
- Latest news.
- SEC/filing updates.
- Earnings/fundamental context.
- Bullish factors.
- Bearish factors.
- Watchlist signals.
- Risks.
- Sources.
- Disclaimer.

### Market Strategy Research

- Current market backdrop.
- Key drivers.
- Sectors to monitor.
- Macro dependencies.
- Housing/rate implications.
- Scenario table.
- Risks.
- Sources.
- Disclaimer.

## Report Templates

### Daily Briefing Template

```text
Title
As of timestamp
Disclaimer

Executive Summary
Top Cross-Market Themes
World and Geopolitics
U.S. Economy and Policy
Markets and Rates
Companies and Earnings
Housing and Real Estate
Commodities and Energy
Technology and AI
Banking and Credit
Consumer and Labor
Regulation and Legal
Watchlist Signals
Risks and Uncertainties
Sources
```

### Company Research Template

```text
Title
As of timestamp
Disclaimer

Company Snapshot
Latest News
SEC and Filing Updates
Earnings and Fundamental Context
Bullish Factors
Bearish Factors
Watchlist Signals
Key Risks
What Would Change The View
Sources
```

### Market Strategy Template

```text
Title
As of timestamp
Disclaimer

Current Market Backdrop
Main Drivers
Sector And Asset-Class Themes
Bullish Scenario
Base Scenario
Bearish Scenario
Signals To Monitor
Risks And Unknowns
Sources
```

### Housing And Macro Template

```text
Title
As of timestamp
Disclaimer

Macro Snapshot
Rates And Fed Context
Inflation And Labor
Mortgage Rates
Housing Prices
Sales, Inventory, And Construction
Regional Notes
Market Implications
Risks And Unknowns
Sources
```

## Product Requirements

### Dashboard

- Daily briefing card.
- Market overview.
- Watchlist.
- Housing/macro snapshot.
- Domain filters for the ten news categories.
- Latest reports.
- Source health/status.

The dashboard should be the first screen of the app. It should show useful information immediately, not a marketing landing page.

### Research Workspace

- Agent chat input.
- Report output pane.
- Source/citation panel.
- Save report button.
- Export later.

### Sources Page

- Source catalog table.
- Enable/disable source.
- Last run status.
- Error state.
- API key requirement.
- Legal/use notes.
- Storage policy: metadata-only, excerpt-only, or full text allowed.
- Source type: official API, official RSS, licensed API, dataset, or webpage.

### Settings

- API keys.
- Daily schedule.
- Local database path.
- Watchlist tickers.
- Preferred regions.
- Disclaimer visibility.

## UI Screen Spec

### Dashboard

- Shows today's briefing status.
- Shows last successful ingestion time.
- Shows the ten-domain filter bar.
- Shows watchlist tickers and key news count.
- Shows market, macro, and housing snapshots.
- Shows source health warnings.

### Daily Briefing

- Displays a generated briefing grouped by the ten domains.
- Each section has top stories, market relevance, uncertainty, and sources.
- Includes disclaimer at the top and bottom for market strategy content.

### Source Manager

- Lists all configured sources.
- Shows enabled/disabled status.
- Shows access type, API key requirement, license requirement, and last run.
- Shows legal and storage notes.
- Supports manual source refresh later.

### Watchlist

- Lets the user define tickers and companies to monitor.
- Shows related news, SEC filings, and report links.
- Does not provide direct buy/sell/hold instructions.

### Company Research

- Accepts ticker or company name.
- Shows company profile, latest news, filings, risks, and watchlist signals.
- Links every material claim to sources.

### Macro And Housing

- Shows rates, inflation, employment, mortgage rates, housing supply, sales, and home price indicators.
- Shows data vintage and next release date where available.

### Agent Chat

- Lets the user ask a research question.
- Shows which agents ran.
- Shows citations and guardrail status.
- Saves report output when requested.

### Settings

- Stores local-only configuration.
- Manages API keys through environment variables or local secure storage in a later phase.
- Lets user set daily briefing time, default regions, and watchlist.

## Deployment Research

Recommended implementation path:

1. Build as a web app first.
2. Add local API/backend and SQLite storage.
3. Add Docker Compose for portable local deployment.
4. Wrap with Tauri for desktop distribution after the web app and backend are working.

### Desktop Option

Tauri is the selected desktop path for v1 because the app is local-first and should stay lightweight. It can build `.app` and `.dmg` bundles on macOS.

Electron remains a fallback only if Tauri packaging blocks a required feature later.

### Portable Option

Docker Compose should be the first portable deployment target. The goal should be:

```bash
docker compose up
```

Then the user opens:

```text
http://localhost:3000
```

## Phase 1 Decisions

- Start API/RSS-first, not scraper-first.
- Use the ten-domain news taxonomy as the v1 organizing structure.
- Use Next.js with TypeScript for the frontend.
- Use FastAPI for the backend and agent/data services.
- Use SQLite, SQLAlchemy, and Alembic for local-first storage.
- Use OpenAI API first behind a provider abstraction.
- Use Tauri later for desktop packaging.
- Use Docker Compose for the first portable deployment path.
- Store metadata, summaries, and citations before storing full article text.
- Use official economic and housing datasets for macro/housing.
- Use user-provided API keys for market data and premium news.
- Build the first app as a local web dashboard.
- Add desktop packaging after core app flows work.
- Treat every strategy answer as research, scenario analysis, and watchlist context, not advice.

## Remaining User Configuration

These choices can be configured during Phase 2 and do not block the build:

- Initial watchlist tickers.
- Preferred housing regions.
- User contact email for responsible API/scraper user-agent strings.
- Which optional paid/free-tier APIs the user wants to enable: Alpha Vantage, Finnhub, NewsAPI, GDELT, Polygon, Nasdaq Data Link, AP, Reuters.
- Whether the first distributed build should prioritize personal Mac use or broader cross-platform use.

## Suggested Phase 2 Build Scope

The next phase should create the actual scaffold:

- Next.js frontend with TypeScript.
- FastAPI backend.
- SQLite database with SQLAlchemy models and Alembic migrations.
- Source catalog configuration.
- Daily briefing dashboard shell.
- Source manager screen shell.
- Settings screen shell.
- First ingestion path using RSS/API sources.
- Guardrail/disclaimer component.
- Basic agent request/response contract.
- Docker Compose for local portable execution.

## Phase 1 Completion Checklist

- [x] Product vision defined.
- [x] Financial-disclaimer guardrails defined.
- [x] Local desktop and portable deployment goals defined.
- [x] Recommended architecture selected.
- [x] V1 news-domain taxonomy selected.
- [x] Source strategy selected.
- [x] Initial source catalog defined.
- [x] Scraping and data-use compliance rules defined.
- [x] Citation policy defined.
- [x] Multi-agent architecture defined.
- [x] Agent input/output contracts sketched.
- [x] Data model sketched.
- [x] UI screens defined.
- [x] Report templates defined.
- [x] Phase 2 build scope defined.
- [x] Remaining user configuration separated from implementation blockers.

Phase 1 is complete when this document is committed to `main`.

## Research References

- [SEC data APIs](https://data.sec.gov/)
- [SEC developer resources](https://www.sec.gov/about/developer-resources)
- [SEC structured disclosure RSS feeds](https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds)
- [FRED API](https://fred.stlouisfed.org/docs/api/fred/overview.html)
- [U.S. Census Economic Indicators API](https://www.census.gov/data/developers/data-sets/economic-indicators.html)
- [BBC RSS/feed documentation](https://support.bbc.co.uk/platform/feeds/NewsFeeds.htm)
- [AP Media API feeds](https://api.ap.org/media/v/docs/Feeds_and_Linked_Content.htm)
- [Reuters Connect RSS notes](https://liaison.thomsonreuters.com/page/rss-feeds-tech-notes)
- [NewsAPI documentation](https://newsapi.org/docs/endpoints)
- [GDELT Cloud API documentation](https://docs.gdeltcloud.com/API_DOCUMENTATION_GUIDE)
- [Finnhub company news API](https://finnhub.io/docs/api/quote)
- [Alpha Vantage API documentation](https://www.alphavantage.co/documentation/)
- [Nasdaq Data Link documentation](https://docs.data.nasdaq.com/)
- [FHFA House Price Index datasets](https://www.fhfa.gov/house-price-index?tab=HPI+Datasets)
- [Freddie Mac PMMS](https://www.freddiemac.com/pmms)
- [NAR existing-home sales](https://www.nar.realtor/research-and-statistics/housing-statistics/existing-home-sales)
- [Redfin Data Center downloads](https://www.redfin.com/news/data-center/downloads/)
- [Robots Exclusion Protocol RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
- [Google robots.txt guide](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- [Investor.gov investment advisers overview](https://www.investor.gov/introduction-investing/getting-started/working-investment-professional/investment-advisers)
- [Investor.gov robo-advisers bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-45)
- [FINRA Rule 2111 suitability FAQ](https://www.finra.org/rules-guidance/key-topics/suitability/faq)
- [FINRA Rule 2210 communications with the public](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2210)
- [Tauri macOS distribution](https://tauri.app/distribute/app-store/)
- [Electron distribution overview](https://www.electronjs.org/docs/latest/tutorial/distribution-overview)
- [Docker Compose quickstart](https://docs.docker.com/compose/gettingstarted/)
- [Next.js self-hosting](https://nextjs.org/docs/app/guides/self-hosting)
