# Milestone 9.8: End-To-End Phase 9 Local Testing

Status: Baseline Complete, User Review Pending

## Purpose

Run the Phase 9 experience locally before user acceptance testing. The goal is to verify that the redesigned app starts, the main screens load, the chatbot can answer with live evidence, and citations stay hidden unless opened.

## Baseline Checks Completed

- Backend test suite passed.
- Frontend typecheck passed.
- Frontend production build passed.
- Local backend and frontend started successfully with `scripts/start-local.sh`.
- Home screen loaded with the new assistant-first layout.
- Settings/source/daily status data loaded from the backend.
- A live mortgage-rate question completed through the UI.
- The answer used the cleaner trend-oriented answer format.
- Old saved report text is cleaned before display so internal routing lines such as `Coordinator selected:` do not leak into the home/report previews.
- Sources are collapsed behind `View Sources` by default.
- The evidence drawer opens and shows citations, retrieved timestamps, confidence, and source support.
- Nested analysis details remain hidden behind a second drawer.

## Fixes Made During Testing

- Added `cleanAnswerText` in the frontend to remove old internal coordinator lines from previously saved reports.
- Tightened frontend context inference so saved watchlist tickers are not attached to unrelated mortgage/housing questions.
- Tightened backend evidence series selection so broad domain labels do not cause stock quote API evidence to appear in pure mortgage-rate answers.
- Added a regression test proving mortgage-rate evidence can be used without pulling unrelated `FINNHUB:QUOTE:*` items.

## User Review Needed

The baseline is technically ready, but Phase 9 should not be considered fully accepted until the user tests real questions and cards.

User should test:

- Ask a housing question for their location.
- Ask a market setup question.
- Ask a watchlist/company question.
- Click each Quick Briefing card.
- Open `View Sources` and confirm the source details are useful but not noisy.
- Confirm Settings feels understandable and not too crowded.
- Note any answer that feels too long, too generic, too cluttered, or too constrained.

## Validation

- `make backend-test`
- `make frontend-typecheck`
- `make frontend-build`
