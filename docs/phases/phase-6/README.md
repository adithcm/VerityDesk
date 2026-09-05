# Phase 6: Simpler UI And Personalization

Status: Planned

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

- Make one natural-language question box the main app entry point.
- Auto-detect intent/domain/ticker/company/region/time window.
- Hide intent/domain/ticker dropdowns behind Advanced.
- Let the user submit without manually selecting categories.
- Show what the app inferred in plain language, with an option to adjust.

### 6.4 Cleaner Report And Briefing Views

- Simplify Daily Briefing and Reports screens.
- Make report actions easier to understand.
- Separate summary, key points, citations, and raw metadata.
- Keep the disclaimer visible without dominating the screen.
- Make saved reports feel like a library.

### 6.5 Source/API Status UX

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

- Validate simplified flows.
- Update local run and usage docs.
- Document remaining source/API gaps for Phase 7.

## Definition Of Done

- A non-technical user can start with a question instead of configuring dropdowns.
- The dashboard is simpler and easier to follow.
- The app remembers user preferences locally.
- The app can use preferences to personalize suggestions and defaults.
- Source/API status is understandable.
- Remaining source expansion work is clearly handed to Phase 7.
