# Milestone 9.6: Prompt And Answer Format Revamp

Status: Complete

## Purpose

Make card prompts and final chatbot answers clearer, more useful, and more trend-aware.

The user should get simple answers that explain what is happening, what direction major trends are moving, why it matters to their saved context, and what to watch next.

## Answer Shape

The synthesis prompt now asks for this structure when useful:

- Bottom Line
- Major Trends
- What Changed Recently
- Why It Matters
- What To Watch Next
- Uncertainty/Data Gaps

The answer should avoid process language, internal agent names, source paths, retrieval statuses, and long citation dumps.

## Trend Analysis

Prompts now explicitly ask the model to describe whether major trends look:

- strengthening
- weakening
- mixed
- unclear

Trend analysis is included for:

- local housing
- market setup
- watchlist/company moves
- world risk
- daily briefing

## Citation Handling

The main backend summary no longer appends a long Sources section.

Citations still return as structured response data, so the UI can show them inside hidden details/drawer patterns instead of crowding the main answer.

## Card Prompt Updates

The card prompts now ask for:

- a simple answer structure
- major trend analysis
- live web first
- API/local verification
- user-specific context
- uncertainty and data gaps
- no direct buy, sell, or hold recommendations

## Validation

- Backend test suite passes.
- Frontend typecheck passes with the local Node runtime.
- Frontend production build passes with the local Node runtime.
