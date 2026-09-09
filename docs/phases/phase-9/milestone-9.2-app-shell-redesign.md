# Milestone 9.2: App Shell Redesign

Status: Complete

## Purpose

Turn the selected Option I prototype into the real app shell.

This milestone focuses on layout and first-screen product feel. It does not complete the deeper prompt-template, routing-cost, or settings cleanup work planned for later Phase 9 milestones.

## Implemented

- Replaced the old light dashboard shell with a dark neon console shell.
- Added a compact left navigation rail.
- Made the default home view a focused Ask workspace.
- Added a right-side Quick Briefings panel.
- Added personalized card labels that use saved Settings context instead of hardcoded locations.
- Kept the overall Refresh Sources action in the top bar.
- Kept existing backend actions wired into the new shell.
- Hid citations/source details behind an expandable section in the new Ask workspace.
- Updated global page color mode to dark.

## Still Planned

- 9.3 will rebuild Settings into the cleaner dedicated control center.
- 9.4 will review and implement final card prompt templates.
- 9.5 will clean up agent orchestration and reduce unnecessary multi-agent/search usage.
- 9.6 will revamp prompts and final answer style.
- 9.7 will make the citation/evidence drawer consistent across the app.

## Validation

- Frontend typecheck passes with the local Node runtime.
- Frontend production build passes with the local Node runtime.
