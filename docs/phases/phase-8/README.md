# Phase 8: Agent Automation And Flexible Retrieval

Status: Planned

## Goal

Make the agents flexible enough to understand natural-language questions, choose the right sources, retrieve missing information, and return a useful cited answer without requiring manual user setup.

## User Feedback To Address

- The user should not have to choose domains, intents, or tickers for normal questions.
- The user wants less typing and fewer clicks.
- The agent should be able to query beyond currently ingested local data when needed.
- If the local database does not have the answer, the system should try approved source/API retrieval.
- If the system still cannot answer, it should say what is missing and what source would be needed.
- The answer should be natural language first, with details and citations available.

## Target Experience

The user asks:

```text
What are mortgage rates in AZ?
```

The system infers:

- topic: housing/mortgage rates
- region: Arizona
- likely sources: Freddie Mac, FRED, housing sources, state/regional data if available
- workflow: check local data, refresh source/API if stale, retrieve approved live data if needed
- response style: concise natural-language answer with citations and uncertainty

If Arizona-specific mortgage rates are unavailable, the app should explain that clearly and provide the best available national/regional proxy rather than pretending to know.

## Milestones

### 8.1 Query Understanding Layer

- Extract intent, topic, entities, tickers, companies, region, and time window from user questions.
- Support plain-language regions such as "Arizona," "AZ," and "Phoenix."
- Add tests for market, company, housing, macro, and world-news questions.

### 8.2 Automatic Agent Routing

- Route to specialist agents based on inferred query needs.
- Reduce manual routing controls in the main workflow.
- Keep Advanced controls for power users.

### 8.3 Local Evidence First

- Search local articles, observations, and saved reports.
- Determine whether local evidence is fresh enough.
- Identify missing evidence and stale sources.

### 8.4 Live Retrieval Fallback

- Add approved live retrieval paths for sources connected in Phase 7.
- Retrieve targeted source/API data when local evidence is missing.
- Keep source compliance and storage policy rules.

### 8.5 Multi-Step Agent Workflows

- Let the coordinator plan multiple steps:
  - parse question
  - inspect local evidence
  - retrieve more data if needed
  - run specialists
  - synthesize answer
  - apply citations and guardrails
- Track steps for debugging while keeping the UI simple.

### 8.6 Personalized Proactive Automation

- Generate briefings and suggestions based on user preferences.
- Recommend next questions and reports without requiring the user to start from scratch.
- Reduce repeated context entry.

### 8.7 Phase 8 Validation And Docs

- Add evaluation fixtures for flexible real-world questions.
- Validate citation and guardrail behavior.
- Document what live retrieval can and cannot do.

## Definition Of Done

- The normal user path is one question box.
- The agent can infer routing without dropdowns.
- The agent can use local data first and approved live retrieval when needed.
- Regional questions have clear answers or clear missing-data explanations.
- Financial guardrails still prevent direct buy/sell/hold instructions.
