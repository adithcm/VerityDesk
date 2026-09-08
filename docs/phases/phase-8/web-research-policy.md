# Phase 8 Web Research Policy

## Purpose

Phase 8 makes live web research the primary path for flexible, current, local, and broad user questions.

The app should use Tavily to find current credible sources, then use direct APIs and local cached data to verify, quantify, or add historical context.

## What Live Web Retrieval Can Do

- Search the current web for credible source-backed evidence.
- Return citation-ready records with title, URL, publisher, retrieved time, and excerpt.
- Help answer questions that local ingested data does not cover.
- Find current market, company, housing, macro, world news, policy, and regional context.
- Support broad user questions such as:
  - "What is happening with housing in Arizona?"
  - "Where is the S&P 500 right now?"
  - "What changed with Apple this week?"
  - "What should I watch today?"

## What Live Web Retrieval Cannot Guarantee

- It cannot guarantee that every source is complete, correct, or current.
- It cannot guarantee access to paywalled articles or restricted databases.
- It cannot replace official structured data where exact measurements are needed.
- It cannot turn a general web result into financial advice.
- It should not invent exact local data when the source only provides national or proxy data.

## Source Priority

Research priority is:

1. Tavily live web search for current discovery and citations.
2. Official/direct APIs for verification and exact structured data.
3. Local cached data for stored context, history, and fast retrieval.
4. Saved reports for previous analysis and continuity.

## Source Quality

The app assigns source quality labels:

- `primary`: official government/regulator/statistical sources.
- `reputable`: established news and market publications.
- `provider`: connected API/data providers.
- `discovery`: general web sources that may help discovery but need caution.
- `internal`: saved local reports or app-generated context.

## Storage Policy

- Store citation metadata and short excerpts.
- Do not store full article text unless source policy allows it.
- Keep URLs available so users can inspect the source.
- Treat live web evidence as retrieved-at-time context, not permanent truth.

## Answer Policy

The final answer should:

- answer the user directly first
- cite sources for factual/current claims
- say when evidence is uncertain or incomplete
- distinguish national, state, metro, company-specific, or market-wide context
- avoid raw internal agent routing, source-path details, and debug logs
- preserve financial guardrails

The final answer should not:

- tell the user to buy, sell, or hold a security
- present unsupported price targets as recommendations
- pretend local data exists when only national/proxy data was found
- dump every retrieval status into the main response

