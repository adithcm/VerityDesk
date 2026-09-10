# Phase 9.5: Product Differentiation Cleanup

Status: In Progress

## Goal

Make VerityDesk feel like an everyday personal intelligence assistant instead of a better-looking research dashboard.

Phase 9 improved the interface and prompt surface. Phase 9.5 is the bridge before deployment: it should make the app more automatic, more personal, easier to scan, and meaningfully different from asking Codex or ChatGPT manually.

## Product North Star

VerityDesk should be a personal daily intelligence assistant that:

- opens to useful answers that are already generated
- knows the user's location, interests, watchlist, housing markets, and priorities
- watches live web and structured sources automatically
- explains what changed since yesterday or last week
- separates signal from noise
- shows why each item matters to the user
- keeps citations available without overwhelming the screen
- helps users monitor what they care about without giving direct buy/sell/hold advice

## User Feedback To Address

- Preset topic cards should not merely run hardcoded prompts.
- The user should not need to click a card every day just to get the default response.
- The app should show daily answers automatically when opened.
- The chatbot should remain available for custom questions.
- There should be a simple setup/login/profile flow for saving user details and preferences.
- The response format should be clearer, with Markdown-style headers, bold key terms, and shorter sections.
- The app should become more seamless, automatic, helpful, simple, and light on visible context.
- The product should stand out with everyday-use features such as watch items, alerts, change tracking, and widgets.

## Experience Target

Default daily use:

1. User opens VerityDesk.
2. The home page already shows today's personalized topic panels.
3. Each panel has a concise answer, last updated time, signal level, and hidden sources.
4. The user asks a custom question only when they want a deeper or different answer.
5. Settings hold the complexity: profile, sources, schedule, keys, watch items, and preferences.

## Daily Topic Panels

Preset cards should become daily panels with stored generated responses.

Initial panels:

- Daily Briefing
- Local Housing Pulse
- Market Setup
- Watchlist Moves
- World Risk Radar
- Rates And Credit

Each panel should show:

- title
- short personalized summary
- `Last Updated`
- signal label: `High Signal`, `Developing`, `Noise`, or `Watch Later`
- change label: `New`, `Improving`, `Worsening`, `Mixed`, or `No Meaningful Change`
- optional `Refresh` action
- hidden `View Sources` drawer
- one-click follow-up actions such as `Explain This`, `What Changed`, or `Why It Matters To Me`

## Setup And Profile Flow

Before desktop deployment, VerityDesk needs a simple first-time experience.

The setup flow should collect:

- name or local profile label
- location and housing markets
- watchlist tickers and companies
- sectors and topics of interest
- risk style and investing style
- briefing style: quick, balanced, or detailed
- preferred morning/evening briefing time
- source/API status
- optional personal note about goals and current situation

For local desktop, this should start as a local profile rather than cloud authentication. A later cloud phase can add true multi-device account sync if needed.

## Answer Format Target

Answers should render as Markdown-style content:

- `## Bottom Line`
- `## What Changed`
- `## Major Trends`
- `## Why It Matters To You`
- `## What To Watch`
- `## Confidence And Gaps`

Formatting rules:

- bold key terms
- short bullets over long paragraphs
- no visible internal agent names in the main answer
- no long citation dumps in the main answer
- compact financial disclaimer when relevant
- clear uncertainty when evidence is thin or conflicting

## Differentiating Features

Phase 9.5 should introduce or document foundations for:

- what changed since yesterday/last week
- signal vs noise labels
- saved watch items
- personal impact layer
- source-quality/confidence explanation
- morning and evening briefing modes
- one-click deep dives from each panel
- alerts for meaningful changes

## Future Add-On Ideas

These are not all required before deployment, but should be captured so the product can grow beyond a chatbot.

- macOS menu bar summary
- desktop widget with top 3 daily signals
- mortgage/rates tracker widget
- watchlist catalyst widget
- market risk meter widget
- local housing pulse widget
- weekly exportable PDF/email report
- calendar-aware Fed/CPI/earnings alerts
- saved monitors such as "tell me when mortgage rates fall below X"
- voice briefing mode

## Milestones

### 9.5.1 Product Direction Docs

Status: Complete

- Capture the product differentiation goal.
- Document the daily panel model, setup/profile flow, answer format, watch items, alerts, and widget ideas.
- Update the roadmap so this phase sits between Phase 9 and deployment.

Milestone doc: [milestones/9.5.1-product-direction-docs.md](milestones/9.5.1-product-direction-docs.md)

### 9.5.2 Setup And Profile Flow

Status: Complete

- Add first-time setup/onboarding.
- Store local profile details and preferences.
- Make the existing Settings page feel like profile management after setup.
- Keep the flow simple and non-technical.

Milestone doc: [milestones/9.5.2-setup-and-profile-flow.md](milestones/9.5.2-setup-and-profile-flow.md)

### 9.5.3 Daily Topic Panel Model

Status: Complete

- Add stored daily panel records.
- Generate and persist panel responses during daily refresh.
- Show current panel answers on home without requiring a card click.
- Keep manual refresh optional.

Milestone doc: [milestones/9.5.3-daily-topic-panel-model.md](milestones/9.5.3-daily-topic-panel-model.md)

### 9.5.4 Markdown Answer Rendering

Status: Planned

- Update prompts to produce scan-friendly Markdown.
- Render Markdown safely in the frontend.
- Style headers, bold text, bullets, and compact sections.
- Preserve hidden citations.

### 9.5.5 Change Tracking And Signal Labels

Status: Planned

- Compare current panel/report output with prior stored output.
- Add `What Changed` sections.
- Add signal labels such as `High Signal`, `Developing`, `Noise`, and `Watch Later`.
- Add confidence/source-quality explanations.

### 9.5.6 Watch Items And Alerts Foundation

Status: Planned

- Let users save things to watch.
- Track watch item status daily.
- Add alert thresholds and meaningful-change rules.
- Keep notifications local-first for now.

### 9.5.7 Final Simplification And Local Testing

Status: Planned

- Remove leftover visual clutter.
- Test the full daily-use flow locally.
- Tune answer length, panel text, empty states, and setup wording.
- Prepare handoff into Phase 10 desktop deployment.

## Definition Of Done

- The home page can show useful daily topic answers without asking the user to click prompt buttons.
- The setup/profile flow captures enough user context to personalize answers.
- Answers are cleaner and easier to scan.
- The product clearly offers more than manual chatbot search.
- Watch items, alert foundations, and widget ideas are documented or scaffolded.
- Phase 10 can focus on packaging and background-service deployment instead of product design cleanup.
