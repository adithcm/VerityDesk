from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Citation, Report
from app.schemas.agent import AgentCitation
from app.schemas.report import ReportCreateRequest, ReportDeleteResponse, ReportListResponse, ReportResponse
from app.services.guardrails import FINANCIAL_DISCLAIMER


REPORT_TYPE_LABELS = {
    "daily_briefing": "Daily Briefing",
    "company_research": "Company Research",
    "market_strategy": "Market Strategy",
    "housing": "Housing Report",
    "macro": "Macro Report",
}


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


def normalize_symbols(symbols: list[str]) -> list[str]:
    return [symbol.strip().upper() for symbol in symbols if symbol.strip()]


def format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
