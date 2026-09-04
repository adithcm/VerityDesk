from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas.agent import AgentClaim, AgentCitation, AgentContext, AgentQueryRequest, AgentQueryResponse, AgentResult
from app.services.agent_runtime import AgentRegistry, AgentRunLogger, AgentRuntime, build_agent_context
from app.services.guardrails import FINANCIAL_DISCLAIMER, check_investment_guardrails


class CoordinatorAgent:
    name = "CoordinatorAgent"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            summary=build_placeholder_summary(context),
            claims=[
                AgentClaim(
                    claim="InvestorAgent has live ingestion foundations and is preparing real agent synthesis.",
                    claim_type="fact",
                    source_ids=[],
                    confidence="high",
                )
            ],
            citations=[
                AgentCitation(
                    title="InvestorAgent source catalog and ingestion status",
                    supports_claim="The response is based on the configured source catalog and Phase 3 ingestion foundation.",
                )
            ],
            confidence="medium",
            risks=[
                "Specialist domain agents are not implemented yet.",
                "This placeholder response should not be used for actual investment decisions.",
            ],
            follow_up_questions=[
                "Which ticker, market, or housing region should the first specialist agent prioritize?",
            ],
        )


def build_default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(CoordinatorAgent())
    return registry


def build_agent_response(request_id: str, result: AgentResult) -> AgentQueryResponse:
    guardrail = check_investment_guardrails(result.summary)

    return AgentQueryResponse(
        request_id=request_id,
        summary=result.summary,
        agents_ran=[result.agent_name, "CitationAgent", "RiskGuardrailAgent"],
        claims=result.claims,
        citations=result.citations,
        confidence=result.confidence,
        risks=result.risks,
        follow_up_questions=result.follow_up_questions,
        guardrail=guardrail,
        requires_guardrail_review=guardrail.status != "passed",
    )


def build_placeholder_summary(context: AgentContext) -> str:
    domains = ", ".join(context.domains) if context.domains else "the configured news domains"
    tickers = ", ".join(context.tickers) if context.tickers else "no specific tickers"

    return (
        f"{FINANCIAL_DISCLAIMER}\n\n"
        "InvestorAgent received the research request and routed it through the "
        "agent runtime coordinator. "
        f"Intent: {context.intent}. Domains: {domains}. Tickers: {tickers}. "
        "Specialist agents, citations from ingested records, and strategy synthesis "
        "will be implemented in Phase 4 milestones. This is not a recommendation "
        "to buy, sell, or hold any security."
    )


def run_agent_query(request: AgentQueryRequest, session: Session | None = None) -> AgentQueryResponse:
    request_id = str(uuid4())
    context = build_agent_context(request_id, request)
    runtime = AgentRuntime(build_default_registry(), AgentRunLogger(session))
    result = runtime.run("CoordinatorAgent", context)
    response = build_agent_response(request_id, result)

    if session is not None:
        session.commit()

    return response
