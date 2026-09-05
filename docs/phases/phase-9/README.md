# Phase 9: Final UI, Prompting, And Product Polish

Status: Planned

## Goal

Make InvestorAgent feel polished after the core data and agent functionality is in place.

The user is not yet fully happy with the UI or with some generated outputs, but part of that dissatisfaction comes from missing data, scaffolded sources, incomplete parsers, and limited agent retrieval. This phase intentionally waits until after Phase 7 and Phase 8 so the final design can be based on real working functionality instead of designing around temporary gaps.

## User Feedback To Address

- The UI still does not feel simple or polished enough.
- Some generated briefings include empty or low-value sections because the data layer is incomplete.
- The app should feel more personal and less like a dashboard.
- The user should not need to scan many lists or understand internal system details.
- The app should provide clearer, more useful natural-language output.
- Prompting should produce better briefings and answers once the source coverage is stronger.

## Timing

Phase 9 happens after:

- Phase 7 completes source expansion, parser completion, and regional data improvements.
- Phase 8 completes flexible agent retrieval and better automatic workflows.

This phase happens before:

- desktop packaging
- portable deployment
- broader quality/evaluation work

## Milestones

### 9.1 Product UX Review

- Review the full app with real Phase 7 data and Phase 8 agent behavior.
- Identify remaining confusing screens, excessive detail, and repeated manual actions.
- Document the final product shape before packaging.

### 9.2 Dashboard Layout Polish

- Refine the first screen around the user’s personalized priorities.
- Reduce secondary panels further if they still feel noisy.
- Improve hierarchy, spacing, labels, empty states, and calls to action.

### 9.3 Briefing And Report Output Polish

- Improve how daily briefings, reports, citations, and uncertainty are presented.
- Make empty/no-data sections less prominent and more useful.
- Improve wording for missing data, stale data, and source limitations.

### 9.4 Prompting And Response Quality Pass

- Refine agent prompts after the data layer is more complete.
- Improve natural-language synthesis.
- Reduce repetitive caveats while keeping financial guardrails.
- Improve answer structure for housing, market, company, macro, and world-news questions.

### 9.5 Navigation And Workflow Cleanup

- Remove or hide workflows that are no longer needed after automation improves.
- Make the main path feel like:
  - open app
  - see what matters
  - ask one question
  - inspect sources only when needed

### 9.6 Phase 9 Validation And Docs

- Validate the final local web app experience.
- Update screenshots or usage notes if needed.
- Confirm readiness for desktop packaging.

## Definition Of Done

- The app feels cleaner and more polished with real connected data.
- Daily briefings and answers are more useful and less sparse.
- The main workflow requires minimal manual setup.
- Raw details are available but do not dominate the experience.
- The product is ready to be packaged as a local desktop app in the next phase.
