# Milestone 9.5: Agent Orchestration Cleanup

Status: Complete

## Purpose

Make the backend routing smarter and reduce unnecessary Tavily/API usage.

The user should experience one assistant. Internally, VerityDesk should select only the agents that matter for the question and should share one evidence packet across specialists.

## Implemented

- Tightened specialist routing rules.
- Daily briefing remains broad and can use all major specialists.
- Housing questions route to Housing and Macro by default.
- Mortgage/rate-heavy housing questions also include Market.
- Broad market ETF questions such as SPY and QQQ no longer trigger CompanyAgent by default.
- Company-specific tickers and company names still route to CompanyAgent.
- World-risk questions start with NewsDigestAgent and include MarketAgent only when spillover context is relevant.
- Generic quick updates still include NewsDigestAgent and MarketAgent.
- Tavily live web retrieval is capped to one shared search per evidence packet.
- The shared Tavily search now requests a slightly larger result set so agents can reuse one richer packet.
- Card-style prompts use the first task line for live web search instead of sending the entire saved profile context as the search query.
- Personalization no longer injects watchlist tickers into unrelated housing or broad market questions.

## Why This Matters

Before this milestone, a question could route to too many agents because saved watchlist context or broad ticker detection made the system over-select CompanyAgent. The system also allowed more than one Tavily query in a single evidence packet.

After this milestone, the app is closer to:

- one user question
- one research plan
- one shared live-web evidence packet
- only needed specialists
- one clean synthesized answer

## Still Planned

- 9.6 will improve the prompt wording and final answer format.
- 9.7 will make hidden citations and evidence drawers consistent across the rest of the app.
- Future backend work can add more advanced search budgeting, such as allowing extra Tavily searches only when the planner explicitly marks them necessary.

## Validation

- Backend test suite passes.
- Added/updated tests for:
  - market ETF routing without CompanyAgent
  - company ticker routing with CompanyAgent
  - world-risk routing
  - one shared live web search per evidence packet
  - Phase 8 regression behavior with the tighter routing
