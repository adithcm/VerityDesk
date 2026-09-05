# Phase 6: Simpler UI And Personalization

Status: Complete

## Goal

Make InvestorAgent feel like a personal intelligence desk instead of an internal operations dashboard.

The user should not need to understand the app's internal domains, agent routing, ingestion runs, source status details, or report mechanics to get value. The normal workflow should be: open the app, see a clear summary of what matters, ask one natural-language question, and let the system infer the rest.

## User Feedback To Address

- There is too much information on the screen.
- Too many panels compete for attention.
- The user has to move between too many places to retrieve information.
- Agent Chat requires too much manual setup.
- The user should not have to keep changing dropdowns.
- The user should not have to type tickers separately in the main workflow.
- The only required typing should be the question.
- The app should personalize itself around the user's situation, interests, location, watchlist, and needs.
- Technical/source details should be visible when useful, but should not overwhelm the first screen.

## Product Direction

InvestorAgent should become a single place where the user can personalize what they care about and receive source-backed daily intelligence without checking many websites manually.

Examples:

- "What matters for my watchlist today?"
- "What are mortgage rates in AZ?"
- "How does the latest rate data affect housing?"
- "What changed with Apple this week?"
- "What should I monitor in markets this morning?"

The app should infer:

- intent
- news domains
- tickers
- companies
- region/location
- time window
- needed agents
- likely report type
- whether advanced controls are needed

## Milestones

### 6.1 UI Information Architecture Cleanup

Status: Complete

- Reduce first-screen clutter.
- Group operational details under Sources/System Status.
- Make Dashboard focus on today's briefing, suggested next steps, and saved reports.
- Move raw ingestion/source diagnostics out of the primary path.
- Keep citations and technical metadata available through expandable panels.

### 6.2 Personalization Profile

Status: Complete

- Add editable preferences for:
  - default location/region
  - watchlist tickers
  - sectors/industries
  - housing interests
  - macro interests
  - topics to prioritize
  - topics to ignore
  - preferred briefing time
- Store preferences locally.
- Use preferences in proactive suggestions and report defaults.

### 6.3 One-Question Primary Workflow

Status: Complete

- Make one natural-language question box the main app entry point.
- Auto-detect intent/domain/ticker/company/region/time window.
- Hide intent/domain/ticker dropdowns behind Advanced.
- Let the user submit without manually selecting categories.
- Show what the app inferred in plain language, with an option to adjust.

### 6.4 Cleaner Report And Briefing Views

Status: Complete

- Simplify Daily Briefing and Reports screens.
- Make report actions easier to understand.
- Separate summary, key points, citations, and raw metadata.
- Keep the disclaimer visible without dominating the screen.
- Make saved reports feel like a library.

### 6.5 Source/API Status UX

Status: Complete

- Show source state in user-friendly terms:
  - Working
  - Missing API key
  - Parser not implemented
  - Scaffolded only
  - Stale
  - Skipped
  - Failed
- Explain what the user can do next.
- Make API-key setup clearer without exposing secrets.

### 6.6 Phase 6 Validation And Docs

Status: Complete

- Validate simplified flows.
- Update local run and usage docs.
- Document remaining source/API gaps for Phase 7.

## Completed Phase 6 Capabilities

- Dashboard is now focused on one question, the latest briefing, quick questions, saved reports, and a compact status summary.
- Detailed ingestion health, source diagnostics, latest raw items, and recent runs moved out of the default path.
- Personalization is available in Settings and saved locally in the browser.
- The saved profile tracks location, watchlist, companies, priority topics, housing interests, macro interests, ignored topics, briefing style, and briefing time.
- Dashboard quick questions use saved personalization.
- Agent Chat now supports a one-question default workflow.
- Intent, domain, tickers, companies, location, and time window are inferred from the question and saved profile.
- Manual agent controls are hidden under Advanced with an option to return to automatic routing.
- Daily Briefing and Reports are reading-first instead of raw-output-first.
- Citations, raw inputs, metadata, focus details, and technical status are available in expandable sections.
- Sources now uses plain status labels and next-step guidance.

## Handoff To Phase 7

Phase 7 remains responsible for the source/data work that Phase 6 intentionally did not complete:

- Finish scaffolded connectors.
- Add missing parsers.
- Complete Census, FHFA, and Freddie Mac source handling.
- Add or complete optional providers such as Alpha Vantage, Finnhub, NewsAPI, and GDELT.
- Improve regional housing support for questions like "mortgage rates in AZ" or "housing in Phoenix."
- Improve confusing source/series labels when raw provider identifiers still appear.
- Add stronger source fallback behavior when local data is missing or stale.

## Validation Results

- `make frontend-typecheck`: passed.
- `make frontend-build`: passed.
- `git diff --check`: passed.

## Definition Of Done

- A non-technical user can start with a question instead of configuring dropdowns.
- The dashboard is simpler and easier to follow.
- The app remembers user preferences locally.
- The app can use preferences to personalize suggestions and defaults.
- Source/API status is understandable.
- Remaining source expansion work is clearly handed to Phase 7.
