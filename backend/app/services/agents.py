from datetime import datetime
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agents.domain_agents import (
    CompanyAgent,
    HousingAgent,
    MacroAgent,
    MarketAgent,
    NewsDigestAgent,
)
from app.agents.model_client import build_default_summarizer
from app.db.models import AgentRun
from app.schemas.agent import (
    AgentCitation,
    AgentContext,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentResult,
    AgentRunHistoryResponse,
    AgentRunRecord,
)
from app.services.agent_runtime import AgentRegistry, AgentRunLogger, AgentRuntime, build_agent_context
from app.services.citations import format_sources_section
from app.services.guardrails import FINANCIAL_DISCLAIMER, enforce_agent_guardrails
from app.services.research_evidence import ResearchEvidenceRepository


class CoordinatorAgent:
    name = "CoordinatorAgent"

    def run(self, context: AgentContext) -> AgentResult:
        routed_agents = route_agent_names(context)
        return AgentResult(
            agent_name=self.name,
            summary=f"Coordinator selected: {', '.join(routed_agents)}.",
            confidence="medium",
            risks=[
                "Routing is deterministic and based on request metadata plus keyword matching.",
            ],
        )


def build_default_registry(session: Session | None = None) -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(CoordinatorAgent())

    if session is not None:
        repository = ResearchEvidenceRepository(session)
        summarizer = build_default_summarizer()
        registry.register(NewsDigestAgent(repository, summarizer))
        registry.register(CompanyAgent(repository, summarizer))
        registry.register(MarketAgent(repository, summarizer))
        registry.register(MacroAgent(repository, summarizer))
        registry.register(HousingAgent(repository, summarizer))

    return registry


def build_agent_response(
    request_id: str,
    results: list[AgentResult],
    request: AgentQueryRequest | None = None,
) -> AgentQueryResponse:
    citations = dedupe_citations([citation for result in results for citation in result.citations])
    confidence = combined_confidence(results)
    summary = synthesize_agent_results(results, citations)
    guardrail = enforce_agent_guardrails(
        summary,
        request=request or AgentQueryRequest(user_query="unspecified agent request"),
        citations=citations,
        confidence=confidence,
    )
    safe_summary = guardrail.rewritten_text or summary

    return AgentQueryResponse(
        request_id=request_id,
        summary=safe_summary,
        agents_ran=[result.agent_name for result in results] + ["CitationAgent", "RiskGuardrailAgent"],
        claims=[claim for result in results for claim in result.claims],
        citations=citations,
        confidence=confidence,
        risks=dedupe_strings([risk for result in results for risk in result.risks]),
        follow_up_questions=dedupe_strings(
            [question for result in results for question in result.follow_up_questions]
        ),
        guardrail=guardrail,
        requires_guardrail_review=guardrail.status != "passed",
    )


def synthesize_agent_results(results: list[AgentResult], citations: list[AgentCitation] | None = None) -> str:
    coordinator = next((result for result in results if result.agent_name == "CoordinatorAgent"), None)
    specialist_results = [result for result in results if result.agent_name != "CoordinatorAgent"]
    sections = [
        FINANCIAL_DISCLAIMER,
        "",
        "This is not a recommendation to buy, sell, or hold any security.",
        "",
    ]

    if coordinator is not None:
        sections.extend([coordinator.summary, ""])

    if not specialist_results:
        sections.append("No specialist agents were run for this request.")
        return "\n".join(sections)

    sections.append("Specialist findings:")
    for result in specialist_results:
        sections.append(f"- {result.agent_name}: {result.summary}")

    risks = dedupe_strings([risk for result in specialist_results for risk in result.risks])
    if risks:
        sections.extend(["", "Key risks:"])
        sections.extend(f"- {risk}" for risk in risks[:5])

    sections.extend(["", format_sources_section(citations or [])])

    return "\n".join(sections)


def route_agent_names(context: AgentContext) -> list[str]:
    selected: list[str] = []
    text = searchable_context_text(context)

    if context.intent == "daily_briefing" or has_any(text, "news", "briefing", "world", "geopolitics"):
        selected.append("NewsDigestAgent")

    if context.intent == "company_research" or context.tickers or context.companies or has_any(
        text,
        "company",
        "ticker",
        "earnings",
        "filing",
        "revenue",
        "sec",
    ):
        selected.append("CompanyAgent")

    if context.intent == "market_research" or has_any(
        text,
        "market",
        "rates",
        "s&p",
        "sp500",
        "nasdaq",
        "dow",
        "yield",
        "bond",
        "credit",
    ):
        selected.append("MarketAgent")

    if context.intent in {"market_research", "housing_macro_research"} or has_any(
        text,
        "macro",
        "economy",
        "inflation",
        "jobs",
        "labor",
        "unemployment",
        "fed",
        "gdp",
    ):
        selected.append("MacroAgent")

    if context.intent == "housing_macro_research" or has_any(
        text,
        "housing",
        "mortgage",
        "real estate",
        "home price",
        "rental",
        "affordability",
    ):
        selected.append("HousingAgent")

    if not selected:
        selected.extend(["NewsDigestAgent", "MarketAgent"])

    return dedupe_strings(selected)


def searchable_context_text(context: AgentContext) -> str:
    return " ".join(
        [
            context.user_query,
            context.intent,
            *context.domains,
            *context.tickers,
            *context.companies,
            *context.regions,
        ]
    ).lower()


def has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def combined_confidence(results: list[AgentResult]) -> str:
    specialist_confidences = [
        result.confidence for result in results if result.agent_name != "CoordinatorAgent"
    ]
    if not specialist_confidences:
        return "low"

    if all(confidence == "high" for confidence in specialist_confidences):
        return "high"
    if any(confidence in {"medium", "high"} for confidence in specialist_confidences):
        return "medium"
    return "low"


def dedupe_citations(citations: list[AgentCitation]) -> list[AgentCitation]:
    seen: set[tuple[str | None, str, str | None]] = set()
    deduped: list[AgentCitation] = []
    for citation in citations:
        key = (citation.source_id, citation.title, citation.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped


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
    runtime = AgentRuntime(build_default_registry(session), AgentRunLogger(session))
    results = [runtime.run("CoordinatorAgent", context)]

    if session is not None:
        for agent_name in route_agent_names(context):
            results.append(runtime.run(agent_name, context))

    response = build_agent_response(request_id, results, request)

    if session is not None:
        session.commit()

    return response


def list_agent_runs(session: Session, *, limit: int = 25) -> AgentRunHistoryResponse:
    runs = session.scalars(
        select(AgentRun).order_by(desc(AgentRun.started_at), desc(AgentRun.id)).limit(limit)
    ).all()

    return AgentRunHistoryResponse(
        runs=[
            AgentRunRecord(
                id=run.id,
                request_id=run.request_id,
                agent_name=run.agent_name,
                status=run.status,
                started_at=format_datetime(run.started_at),
                completed_at=format_datetime(run.completed_at),
                error=run.error,
            )
            for run in runs
        ],
        total=len(runs),
    )


def format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
