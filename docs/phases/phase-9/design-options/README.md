# Phase 9 UI Design Options

These are static HTML prototypes for choosing the Phase 9 product direction before implementation.

## Options

- [Option A: Assistant Home](option-a-assistant-home.html)
- [Option B: Command Center](option-b-command-center.html)
- [Option C: Briefing First](option-c-briefing-first.html)
- [Option D: Tech Home](option-d-tech-home.html)
- [Option D: Tech Settings](option-d-tech-settings.html)
- [Option E: Refined Tech Concept](option-e-refined-tech.html)
- [Option F: Console Grid](option-f-console-grid.html)
- [Option F: Control Center](option-f-control-center.html)
- [Option G: Aurora Deck](option-g-aurora-deck.html)
- [Option H: Neon Terminal](option-h-neon-terminal.html)
- [Option I: Selected Neon Console](option-i-selected-neon-console.html)

## Selected Direction

The selected direction is Option H's neon terminal visual style combined with Option F's new layout structure.

Implementation target:

- Home page uses a simple three-zone layout:
  - left compact navigation rail
  - center assistant/chat answer workspace
  - right topic briefing cards
- The user should mostly type only a question.
- Topic cards should trigger ready-made briefings without dropdowns or ticker/context setup.
- Topic cards should use saved Settings context instead of hardcoded regions or companies.
- Live web search should feel primary, with APIs and stored sources used for corroboration.
- The answer should be natural-language first, with sources/citations tucked into details.
- Settings remains a dedicated page for:
  - personal note/context
  - source status and descriptions
  - one overall source refresh button
  - automation settings
  - watchlist, regions, and tracked topics
- Visual system should be darker, futuristic, terminal-inspired, and cleaner than the earlier dashboard layouts.

## Revised Direction From User Feedback

Option F is the structurally different direction after the follow-up feedback.

The updated product shape is:

- Home page:
  - command-console/chat workspace
  - compact side rail for major modes
  - signal board with larger, more visual topic modules
  - cards trigger topic-focused briefings
  - sources and debug detail remain secondary
- Settings page:
  - user preferences
  - personal note box for what the user cares about and how answers should be shaped
  - watchlist
  - preferred regions
  - tracked topics
  - daily briefing schedule
  - source list with plain-language descriptions
  - one overall manual refresh button
  - automatic update status
- Visual style:
  - darker, cleaner, more tech-forward
  - more grid/console inspired
  - stronger contrast and visual structure
  - less beige/soft dashboard styling
  - fewer visible tables/lists on the home page

Useful topic cards for the home page:

- Daily Briefing
- Local Housing Pulse
- Market Setup
- Watchlist Changes
- Macro Radar
- World and Geopolitics
- Rates and Credit
- Company Earnings
- AI and Technology
- Commodities and Energy

The personal note should be included in prompt context for agent chat, topic cards, and daily briefings. It should help the app understand the user's situation without requiring repeated typing.

The housing card should be generic in the UI and personalized at runtime. For example, if the user saves Arizona or Phoenix in Settings, Local Housing Pulse should automatically become an Arizona/Phoenix housing briefing behind the scenes.

## Recommendation

Option F is now the best direction if the app should feel more meaningfully different from the earlier dashboard/cards designs.

Option D remains useful as a simpler fallback if the console direction feels too stylized.

Option G explores a brighter futuristic glass style with more whitespace.

Option H explores a darker terminal-inspired product style with stronger neon accents.

Option C is strongest if the daily briefing should become the main reason to open the app each morning.

Option B is best if you still want a dashboard feel, but it risks showing more navigation and panels than necessary.

## What To Decide

- Should the first screen lead with the question box, the daily briefing, or a dashboard?
- How much source/status detail should be visible by default?
- Should preferences live in a small setup panel, a modal, or a dedicated settings page?
- Should Tavily usage be shown as a small status pill or hidden in details?
