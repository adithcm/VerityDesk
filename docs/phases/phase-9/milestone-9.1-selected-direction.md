# Milestone 9.1: Selected UI Direction

Status: Complete

## Purpose

Lock the Phase 9 product direction before implementing the real app changes.

The main decision is to combine:

- Option F's changed layout structure
- Option H's neon terminal visual style

The selected prototype is [design-options/option-i-selected-neon-console.html](design-options/option-i-selected-neon-console.html).

## Product Principle

VerityDesk should feel like one personal research assistant.

The user should not need to understand agents, source routing, retrieval strategy, APIs, tickers, dropdowns, or debug traces during normal use. The system should infer what is needed, gather evidence, and return a clear answer.

## Home Screen

The home screen should have three areas:

- Left rail: compact navigation between Ask, Daily Briefing, Local Housing, Risk, Watchlist, and Settings.
- Center workspace: the chatbot question box, current answer, and concise status.
- Right panel: one-click personalized briefing cards.

The home screen should not show large source tables, raw agent output, or long citation lists by default.

## Main Chatbot

The chatbot should:

- accept one plain-language user question
- infer intent and context automatically
- use Tavily/live web as the primary retrieval path for current or flexible questions
- use APIs and stored data as verification and support
- route only to the necessary internal agents
- synthesize one natural-language answer
- keep citations and evidence details hidden behind a disclosure control
- include financial guardrails without overwhelming the response

## Personalized Cards

Cards should act like prebuilt questions, not static reports.

Cards should use saved settings:

- saved location or preferred regions
- saved watchlist
- saved topics and interests
- saved answer style
- saved daily schedule

Initial cards:

- Daily Briefing
- Local Housing Pulse
- Market Setup
- Watchlist Moves
- World Risk Radar

The Local Housing Pulse card must not be hardcoded to Arizona. It should use the user's saved location. Arizona can appear only as example profile data when the user has configured Arizona.

Card prompts will be reviewed again before Milestone 9.4.

## Settings Screen

Settings should hold complexity that no longer belongs on the home screen:

- personal note/context
- preferred location and regions
- watchlist
- tracked topics
- source status and descriptions
- one overall source refresh action
- daily briefing automation
- API/source connection health

The settings page should explain sources in plain language.

## Citations

Citations should be hidden by default.

The main answer should show:

- direct answer
- brief reasoning
- what changed
- what matters
- what to watch

The hidden details section should show:

- citations and URLs
- source type
- retrieved at timestamp
- confidence
- evidence notes
- whether the evidence came from web search, direct APIs, or local stored data

## Visual Direction

The visual design should be:

- dark
- futuristic
- terminal-inspired
- clean
- structured
- readable
- less dashboard-heavy

Avoid making the UI feel like a source-monitoring table or internal debugging console. The terminal style should communicate intelligence and speed, while the experience remains simple for non-technical users.

## Acceptance Criteria

- Phase 9 README documents the selected product direction.
- Design options README points to Option I as the selected prototype.
- Option I shows the selected layout and visual style.
- Option I buttons allow basic screen switching for design review.
- The docs state that citations are hidden by default.
- The docs state that cards use Settings personalization instead of hardcoded values.
