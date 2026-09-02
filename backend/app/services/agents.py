from uuid import uuid4

from app.schemas.agent import AgentClaim, AgentCitation, AgentQueryRequest, AgentQueryResponse
from app.services.guardrails import FINANCIAL_DISCLAIMER, check_investment_guardrails


class CoordinatorAgent:
    name = "CoordinatorAgent"

    def run(self, request: AgentQueryRequest) -> AgentQueryResponse:
        summary = build_placeholder_summary(request)
        guardrail = check_investment_guardrails(summary)

        return AgentQueryResponse(
            request_id=str(uuid4()),
            summary=summary,
            agents_ran=[self.name, "CitationAgent", "RiskGuardrailAgent"],
            claims=[
                AgentClaim(
                    claim="InvestorAgent has not connected live source ingestion yet.",
                    claim_type="fact",
                    source_ids=[],
                    confidence="high",
                )
            ],
            citations=[
                AgentCitation(
                    title="InvestorAgent source catalog",
                    supports_claim="The response is based on the configured source catalog scaffold.",
                )
            ],
            confidence="medium",
            risks=[
                "Live ingestion and source retrieval are not implemented in Phase 2.5.",
                "This placeholder response should not be used for actual investment decisions.",
            ],
            follow_up_questions=[
                "Which ticker, market, or housing region should be prioritized when ingestion begins?",
            ],
            guardrail=guardrail,
            requires_guardrail_review=guardrail.status != "passed",
        )


def build_placeholder_summary(request: AgentQueryRequest) -> str:
    domains = ", ".join(request.domains) if request.domains else "the configured news domains"
    tickers = ", ".join(request.tickers) if request.tickers else "no specific tickers"

    return (
        f"{FINANCIAL_DISCLAIMER}\n\n"
        "InvestorAgent received the research request and routed it through the "
        "placeholder coordinator. "
        f"Intent: {request.intent}. Domains: {domains}. Tickers: {tickers}. "
        "Live research, citations from fetched articles, and strategy synthesis "
        "will be implemented in later milestones. This is not a recommendation "
        "to buy, sell, or hold any security."
    )


def run_agent_query(request: AgentQueryRequest) -> AgentQueryResponse:
    return CoordinatorAgent().run(request)
