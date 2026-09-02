# Phase 2

Status: In progress

Phase 2 builds the runnable application scaffold: frontend, backend, database foundation, source catalog foundation, agent contracts, guardrail contracts, and first UI shell.

## Completed Milestones

- [Milestone 2.1: Repo And Tooling Scaffold](milestones/2.1-repo-and-tooling-scaffold.md)
- [Milestone 2.2: Backend Foundation](milestones/2.2-backend-foundation.md)
- [Milestone 2.3: Database Foundation](milestones/2.3-database-foundation.md)
- [Milestone 2.4: Source Catalog Foundation](milestones/2.4-source-catalog-foundation.md)

## Next Milestone

### Milestone 2.5: Agent And Guardrail Contracts

Goal: add structured agent request/response schemas, placeholder coordinator/citation/guardrail services, and a safe `POST /api/v1/agents/query` endpoint.

Expected deliverables:

- Agent request/response schemas.
- Claim/citation/risk schema objects.
- Placeholder `CoordinatorAgent` service.
- Placeholder `CitationAgent` service.
- `RiskGuardrailAgent` skeleton.
- Shared financial disclaimer text.
- Basic banned direct-advice phrase checks.
- `POST /api/v1/agents/query` endpoint returning structured placeholder output.
- Tests for safe agent output and guardrail behavior.
