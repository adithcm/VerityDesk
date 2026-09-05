from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Citation, Report, Source
from app.schemas.agent import AgentCitation, AgentQueryRequest, AgentQueryResponse
from app.schemas.report import (
    DailyBriefingRequest,
    ReportCreateRequest,
    ReportDeleteResponse,
    ReportListResponse,
    ReportResponse,
)
from app.services.agents import run_agent_query
from app.services.guardrails import FINANCIAL_DISCLAIMER


REPORT_TYPE_LABELS = {
    "daily_briefing": "Daily Briefing",
    "company_research": "Company Research",
    "market_strategy": "Market Strategy",
    "housing": "Housing Report",
    "macro": "Macro Report",
}

DAILY_BRIEFING_DOMAINS = [
    "World and Geopolitics",
    "U.S. Economy and Policy",
    "Markets and Rates",
    "Companies and Earnings",
    "Housing and Real Estate",
    "Commodities and Energy",
    "Technology and AI",
    "Banking and Credit",
    "Consumer and Labor",
    "Regulation and Legal",
]


def create_report(session: Session, request: ReportCreateRequest) -> ReportResponse:
    now = datetime.now(UTC)
    report = Report(
        report_type=request.report_type,
        status="draft",
        title=request.title or default_report_title(request, now),
        summary="Report shell created. Full generation will be added in later Phase 5 milestones.",
        body=build_report_shell_body(request),
        domains=request.domains,
        tickers=normalize_symbols(request.tickers),
        companies=request.companies,
        as_of=now,
        confidence="low",
        disclaimer_version="v1",
        guardrail_status="passed",
        report_metadata={
            "user_query": request.user_query,
            "regions": request.regions,
            "time_window": request.time_window,
            "generation_stage": "contract_shell",
        },
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report_to_response(report)


def generate_daily_briefing(session: Session, request: DailyBriefingRequest) -> ReportResponse:
    now = datetime.now(UTC)
    domains = request.domains or DAILY_BRIEFING_DOMAINS
    query = request.user_query or (
        "Generate a concise daily briefing covering the most important current world, market, macro, company, "
        "housing, policy, credit, commodity, technology, consumer, and legal signals from the ingested evidence."
    )
    agent_request = AgentQueryRequest(
        user_query=query,
        intent="daily_briefing",
        domains=domains,
        regions=request.regions,
        time_window=request.time_window,
        safety_level="investment_research",
    )
    agent_response = run_agent_query(agent_request, session)

    report = Report(
        report_type="daily_briefing",
        status="generated",
        title=request.title or default_report_title(ReportCreateRequest(report_type="daily_briefing"), now),
        summary=build_report_summary(agent_response),
        body=agent_response.summary,
        domains=domains,
        tickers=[],
        companies=[],
        as_of=now,
        confidence=agent_response.confidence,
        disclaimer_version="v1",
        guardrail_status=agent_response.guardrail.status,
        report_metadata={
            "user_query": query,
            "regions": request.regions,
            "time_window": request.time_window,
            "generation_stage": "daily_briefing",
            "agent_request_id": agent_response.request_id,
            "agents_ran": agent_response.agents_ran,
            "requires_guardrail_review": agent_response.requires_guardrail_review,
            "follow_up_questions": agent_response.follow_up_questions,
            "risks": agent_response.risks,
        },
    )
    session.add(report)
    session.flush()
    add_report_citations(session, report, agent_response.citations)
    session.commit()
    session.refresh(report)
    return get_report(session, report.id)


def list_reports(session: Session, *, limit: int = 25, report_type: str | None = None) -> ReportListResponse:
    statement = select(Report).options(joinedload(Report.citations)).order_by(desc(Report.created_at), desc(Report.id))
    if report_type:
        statement = statement.where(Report.report_type == report_type)

    reports = session.scalars(statement.limit(limit)).unique().all()
    return ReportListResponse(
        reports=[report_to_response(report) for report in reports],
        total=len(reports),
    )


def get_report(session: Session, report_id: int) -> ReportResponse:
    report = session.scalar(
        select(Report).options(joinedload(Report.citations).joinedload(Citation.source)).where(Report.id == report_id)
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return report_to_response(report)


def delete_report(session: Session, report_id: int) -> ReportDeleteResponse:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    session.delete(report)
    session.commit()
    return ReportDeleteResponse(id=report_id, deleted=True)


def add_report_citations(session: Session, report: Report, citations: list[AgentCitation]) -> None:
    source_by_key = {source.name: source for source in session.scalars(select(Source)).all()}
    for citation in citations:
        source = source_for_citation(session, source_by_key, citation)
        if source is None:
            continue
        report.citations.append(
            Citation(
                source=source,
                url=citation.url or "",
                title=citation.title,
                publisher=citation.publisher,
                published_at=parse_datetime(citation.published_at),
                retrieved_at=parse_datetime(citation.retrieved_at),
                supports_claim=citation.supports_claim,
            )
        )


def report_to_response(report: Report) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        report_type=report.report_type,
        status=report.status,
        title=report.title,
        summary=report.summary,
        body=report.body,
        domains=report.domains,
        tickers=report.tickers,
        companies=report.companies,
        as_of=format_datetime(report.as_of),
        confidence=report.confidence,
        disclaimer_version=report.disclaimer_version,
        guardrail_status=report.guardrail_status,
        metadata=report.report_metadata,
        citations=[citation_to_agent_citation(citation) for citation in report.citations],
        created_at=format_datetime(report.created_at) or "",
        updated_at=format_datetime(report.updated_at) or "",
    )


def citation_to_agent_citation(citation: Citation) -> AgentCitation:
    source_name = citation.source.name if citation.source else None
    return AgentCitation(
        source_id=source_name,
        title=citation.title,
        url=citation.url,
        publisher=citation.publisher or source_name,
        published_at=format_datetime(citation.published_at),
        retrieved_at=format_datetime(citation.retrieved_at),
        supports_claim=citation.supports_claim,
    )


def source_for_citation(
    session: Session,
    source_by_key: dict[str, Source],
    citation: AgentCitation,
) -> Source | None:
    candidates = [
        citation.source_id,
        citation.publisher,
    ]
    for candidate in candidates:
        if candidate and candidate in source_by_key:
            return source_by_key[candidate]

    if not citation.source_id:
        return None

    source = Source(
        name=citation.source_id,
        base_url=None,
        source_type="citation",
        domains=[],
        access_method="generated_report",
        enabled=True,
    )
    session.add(source)
    session.flush()
    source_by_key[source.name] = source
    return source


def default_report_title(request: ReportCreateRequest, as_of: datetime) -> str:
    label = REPORT_TYPE_LABELS[request.report_type]
    date = as_of.date().isoformat()
    if request.tickers:
        return f"{label}: {', '.join(normalize_symbols(request.tickers))} ({date})"
    if request.companies:
        return f"{label}: {', '.join(request.companies)} ({date})"
    return f"{label} ({date})"


def build_report_shell_body(request: ReportCreateRequest) -> str:
    context_lines = [
        FINANCIAL_DISCLAIMER,
        "",
        "This report shell confirms the request and saved-report contract. Full source-backed generation is planned for later Phase 5 milestones.",
        "",
        f"Report type: {REPORT_TYPE_LABELS[request.report_type]}",
    ]
    if request.user_query:
        context_lines.append(f"User request: {request.user_query}")
    if request.domains:
        context_lines.append(f"Domains: {', '.join(request.domains)}")
    if request.tickers:
        context_lines.append(f"Tickers: {', '.join(normalize_symbols(request.tickers))}")
    if request.companies:
        context_lines.append(f"Companies: {', '.join(request.companies)}")

    return "\n".join(context_lines)


def build_report_summary(agent_response: AgentQueryResponse) -> str:
    lines = [line.strip() for line in agent_response.summary.splitlines() if line.strip()]
    for line in lines:
        if "financial advice" in line.lower() or "not a recommendation" in line.lower():
            continue
        return line[:500]
    return "Daily briefing generated from current ingested evidence."


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def normalize_symbols(symbols: list[str]) -> list[str]:
    return [symbol.strip().upper() for symbol in symbols if symbol.strip()]


def format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
