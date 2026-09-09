# Milestone 9.7: Hidden Citations And Evidence Drawer

Status: Complete

## Purpose

Keep the main assistant answer easy to read while preserving source transparency for users who want to inspect the evidence.

Phase 9 moved the product toward a simpler assistant-first experience. This milestone completes the citation side of that work: sources remain available, but they no longer dominate the screen or interrupt the answer.

## Implemented Behavior

- Main chatbot answers show the readable response first.
- Source and evidence details are hidden by default behind a `View Sources` drawer.
- The drawer shows citation count, confidence, latest retrieved timestamp, and guardrail/review status.
- Citations include source title, publisher/source id, published date, retrieved date, link, and what the citation supports.
- Deeper analysis details such as agents run, structured claims, risks, follow-up questions, and guardrail review are nested behind a second details section.
- Report previews and report reading panels use the same hidden evidence pattern.

## User Experience

Default view:

- answer
- compact confidence/source count chips
- short financial disclaimer when relevant

Expanded evidence view:

- citations
- retrieved timestamps
- confidence
- guardrail status
- source links
- supporting claims
- risks and follow-up questions

This keeps VerityDesk from feeling like a technical dashboard while still making the evidence available.

## Files Updated

- `frontend/src/app/page.tsx`
- `docs/phases/phase-9/README.md`

## Validation

- `make frontend-typecheck`
