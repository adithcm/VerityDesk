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
from app.schemas.evidence_packet import EvidencePacket
from app.services.agent_runtime import AgentRegistry, AgentRunLogger, AgentRuntime, build_agent_context
from app.services.citations import format_sources_section
from app.services.evidence_fusion import build_evidence_packet
from app.services.guardrails import (
    FINANCIAL_DISCLAIMER,
    enforce_agent_guardrails,
    find_banned_direct_advice_phrases,
)
from app.services.personalization import personalize_agent_request
from app.services.research_evidence import ResearchEvidenceRepository
from app.services.research_workflow import build_research_workflow_plan


class CoordinatorAgent:
    name = "CoordinatorAgent"

    def run(self, context: AgentContext) -> AgentResult:
        routed_agents = route_agent_names(context)
        plan = build_research_workflow_plan(context, routed_agents)
        primary_channel = plan.retrieval_priority[0] if plan.retrieval_priority else "local_cache"
        return AgentResult(
            agent_name=self.name,
            summary=(
                f"Coordinator selected: {', '.join(routed_agents)}. "
                f"Research plan starts with {primary_channel.replace('_', ' ')} and then uses "
                "supporting API/local evidence before synthesis."
            ),
            confidence="medium",
            risks=[
                "Live web retrieval depends on a configured search provider API key.",
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
    evidence_packet: EvidencePacket | None = None,
) -> AgentQueryResponse:
    citations = dedupe_citations(
        [citation for result in results for citation in result.citations]
        + (evidence_packet.citations if evidence_packet is not None else [])
    )
    confidence = combined_confidence(results)
    summary = synthesize_agent_results(results, citations, request, evidence_packet)
    guardrail = enforce_agent_guardrails(
        summary,
        request=request or AgentQueryRequest(user_query="unspecified agent request"),
        citations=citations,
        confidence=confidence,
    )
    hidden_banned_phrases = find_banned_direct_advice_phrases(
        " ".join(result.summary for result in results)
    )
    if hidden_banned_phrases and guardrail.status != "blocked":
        guardrail = guardrail.model_copy(
            update={
                "status": "blocked",
                "issues": dedupe_strings(
                    [
                        *guardrail.issues,
                        "Specialist output contained direct investment advice wording.",
                    ]
                ),
                "banned_phrases_found": dedupe_strings(
                    [*guardrail.banned_phrases_found, *hidden_banned_phrases]
                ),
            }
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


def synthesize_agent_results(
    results: list[AgentResult],
    citations: list[AgentCitation] | None = None,
    request: AgentQueryRequest | None = None,
    evidence_packet: EvidencePacket | None = None,
) -> str:
    specialist_results = [result for result in results if result.agent_name != "CoordinatorAgent"]
    sections = [
        FINANCIAL_DISCLAIMER,
        "",
        "This is not a recommendation to buy, sell, or hold any security.",
        "",
    ]

    if not specialist_results:
        sections.append("I do not have enough specialist research to answer this yet.")
        return "\n".join(sections)

    sections.append(
        build_natural_language_answer(
            specialist_results,
            citations or [],
            request or AgentQueryRequest(user_query="unspecified agent request"),
            evidence_packet,
        )
    )

    watch_items = build_watch_items(specialist_results, evidence_packet)
    if watch_items:
        sections.extend(["", "What To Watch:"])
        sections.extend(f"- {item}" for item in watch_items[:4])

    sections.extend(["", format_sources_section(citations or [])])

    return "\n".join(sections)


def build_natural_language_answer(
    specialist_results: list[AgentResult],
    citations: list[AgentCitation],
    request: AgentQueryRequest,
    evidence_packet: EvidencePacket | None = None,
) -> str:
    evidence = format_synthesis_evidence(specialist_results, citations, request, evidence_packet)
    if not evidence.strip():
        return "I do not have enough current source-backed evidence to answer this yet. Run ingestion first, then ask again."

    return build_default_summarizer().summarize(
        agent_name="SynthesisAgent",
        instructions=(
            "Write a direct, natural-language answer to the user's question in 2-3 short paragraphs. "
            "Start with the answer, not process details. Use the fused evidence packet first, then specialist "
            "summaries as supporting interpretation. Do not mention internal agent names, coordinator routing, "
            "source paths, retrieval statuses, or debug details in the user-facing answer. Mention uncertainty "
            "plainly when evidence is thin or live web retrieval was skipped. "
            "Do not give direct buy, sell, or hold instructions, and do not present price targets as recommendations."
        ),
        evidence=evidence,
    )


def format_synthesis_evidence(
    specialist_results: list[AgentResult],
    citations: list[AgentCitation],
    request: AgentQueryRequest,
    evidence_packet: EvidencePacket | None = None,
) -> str:
    lines = [
        f"User question: {request.user_query}",
        f"Intent: {request.intent}",
    ]

    if request.domains:
        lines.append(f"Requested domains: {', '.join(request.domains)}")
    if request.tickers:
        lines.append(f"Requested tickers: {', '.join(request.tickers)}")

    if evidence_packet is not None:
        lines.append("")
        lines.append("Fused evidence packet:")
        for item in evidence_packet.items[:12]:
            date = item.published_at or item.retrieved_at or "unknown date"
            publisher = item.publisher or item.source_name or item.source_id or item.source_kind
            scope = f", scope: {item.scope}" if item.scope else ""
            lines.append(
                f"- {item.source_kind} | {item.source_quality} | {item.title} "
                f"({publisher}, {date}{scope}) - {item.summary}"
            )

        if evidence_packet.retrieval_statuses:
            lines.append("")
        lines.append("Internal retrieval statuses. Use only to understand coverage gaps; do not quote these as user-facing text:")
        for status in evidence_packet.retrieval_statuses:
            query = f" query={status.query}" if status.query else ""
            lines.append(f"- {status.channel}: {status.status}.{query} {status.message}")

    lines.append("")
    lines.append("Specialist summaries. Use as interpretation only; do not mention agent names in the final answer:")
    for result in specialist_results:
        lines.append(f"- {result.agent_name} ({result.confidence} confidence): {result.summary}")

    if citations:
        lines.append("")
        lines.append("Citations:")
        for citation in citations[:10]:
            date = citation.published_at or citation.retrieved_at or "unknown date"
            publisher = citation.publisher or citation.source_id or "unknown source"
            lines.append(f"- {citation.title} ({publisher}, {date}): {citation.supports_claim}")

    return "\n".join(lines)


def build_watch_items(
    specialist_results: list[AgentResult],
    evidence_packet: EvidencePacket | None,
) -> list[str]:
    items: list[str] = []
    if evidence_packet is not None:
        if any(item.source_kind == "live_web" for item in evidence_packet.items):
            items.append("Whether newer live sources confirm or reverse today's signal.")
        if any(item.source_kind == "direct_api" for item in evidence_packet.items):
            items.append("Whether official/API data confirms the live web narrative.")
        skipped_live = [
            status
            for status in evidence_packet.retrieval_statuses
            if status.channel == "live_web" and status.status != "success"
        ]
        if skipped_live:
            items.append("Live web coverage was limited, so refresh once the source is available.")

    low_confidence_count = sum(1 for result in specialist_results if result.confidence == "low")
    if low_confidence_count:
        items.append("Evidence remains thin in at least one area, so treat conclusions as provisional.")

    return dedupe_strings(items)


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
        "alphabet",
        "amazon",
        "apple",
        "google",
        "meta",
        "microsoft",
        "nvidia",
        "tesla",
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
        "portfolio",
        "watch",
        "watchlist",
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
    if session is not None:
        request = personalize_agent_request(request, session)
    context = build_agent_context(request_id, request)
    runtime = AgentRuntime(build_default_registry(session), AgentRunLogger(session))
    results = [runtime.run("CoordinatorAgent", context)]
    evidence_packet = None

    if session is not None:
        routed_agent_names = route_agent_names(context)
        plan = build_research_workflow_plan(context, routed_agent_names)
        evidence_packet = build_evidence_packet(context=context, plan=plan, session=session)
        context = context.model_copy(update={"evidence_packet": evidence_packet.model_dump()})
        for agent_name in routed_agent_names:
            results.append(runtime.run(agent_name, context))

    response = build_agent_response(request_id, results, request, evidence_packet)
    if evidence_packet is not None:
        response.agents_ran.insert(1, "EvidenceFusionAgent")

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
