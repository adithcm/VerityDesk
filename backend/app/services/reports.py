from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Citation, Report, Source
from app.schemas.agent import AgentCitation, AgentQueryRequest, AgentQueryResponse
from app.schemas.preferences import UserPreferencesResponse
from app.schemas.report import (
    CompanyResearchRequest,
    DailyBriefingRequest,
    HousingReportRequest,
    MacroReportRequest,
    MarketStrategyRequest,
    ReportCreateRequest,
    ReportDeleteResponse,
    ReportListResponse,
    ReportResponse,
)
from app.services.agents import run_agent_query
from app.services.guardrails import FINANCIAL_DISCLAIMER
from app.services.personalization import read_user_preferences


DEFAULT_DAILY_WATCHLIST = ["SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
DEFAULT_DAILY_BRIEFING_TOPICS = [
    "main world news",
    "geopolitical risk globally and in the United States",
    "major AI news around the world and in the United States",
    "major technology company developments",
    "S&P 500 setup and trend",
    "watchlist stock trends",
    "rates, macro, housing, and consumer signals",
]

REPORT_TYPE_LABELS = {
    "daily_briefing": "Daily Briefing",
    "company_research": "Company Research",
    "market_strategy": "Market Strategy",
    "housing": "Housing Report",
    "macro": "Macro Report",
}

IMPROVING_TERMS = {
    "improving",
    "improved",
    "easing",
    "cooling",
    "lower",
    "falling",
    "stabilizing",
    "relief",
    "recovering",
    "stronger",
}

WORSENING_TERMS = {
    "worsening",
    "worse",
    "higher risk",
    "spike",
    "rising",
    "tightening",
    "escalation",
    "stress",
    "weakening",
    "deteriorating",
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

COMPANY_RESEARCH_DOMAINS = [
    "Companies and Earnings",
    "Markets and Rates",
    "U.S. Economy and Policy",
    "Technology and AI",
    "Regulation and Legal",
    "Consumer and Labor",
]

MARKET_STRATEGY_DOMAINS = [
    "Markets and Rates",
    "U.S. Economy and Policy",
    "Banking and Credit",
    "Commodities and Energy",
    "Consumer and Labor",
    "World and Geopolitics",
]

HOUSING_REPORT_DOMAINS = [
    "Housing and Real Estate",
    "Markets and Rates",
    "U.S. Economy and Policy",
    "Banking and Credit",
    "Consumer and Labor",
]

MACRO_REPORT_DOMAINS = [
    "U.S. Economy and Policy",
    "Markets and Rates",
    "Consumer and Labor",
    "Banking and Credit",
    "World and Geopolitics",
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
    preferences = read_user_preferences(session)
    domains = request.domains or DAILY_BRIEFING_DOMAINS
    regions = request.regions or preferences.preferred_regions
    tickers = preferences.watchlist_tickers or DEFAULT_DAILY_WATCHLIST
    query = request.user_query or build_personalized_daily_briefing_query(preferences)
    agent_request = AgentQueryRequest(
        user_query=query,
        intent="daily_briefing",
        domains=domains,
        tickers=tickers,
        regions=regions,
        source_ids=preferences.enabled_sources,
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
        tickers=tickers,
        companies=[],
        as_of=now,
        confidence=agent_response.confidence,
        disclaimer_version="v1",
        guardrail_status=agent_response.guardrail.status,
        report_metadata={
            "user_query": query,
            "regions": regions,
            "watchlist_tickers": tickers,
            "enabled_sources": preferences.enabled_sources,
            "personalized": bool(tickers or regions or preferences.enabled_sources),
            "time_window": request.time_window,
            "generation_stage": "daily_briefing",
            "agent_request_id": agent_response.request_id,
            "agents_ran": agent_response.agents_ran,
            "requires_guardrail_review": agent_response.requires_guardrail_review,
            "follow_up_questions": agent_response.follow_up_questions,
            "risks": agent_response.risks,
            **build_panel_signal_metadata(session, "daily_briefing", agent_response),
        },
    )
    session.add(report)
    session.flush()
    add_report_citations(session, report, agent_response.citations)
    session.commit()
    session.refresh(report)
    return get_report(session, report.id)


def build_personalized_daily_briefing_query(preferences: UserPreferencesResponse) -> str:
    watchlist = preferences.watchlist_tickers or DEFAULT_DAILY_WATCHLIST
    focus_parts = list(DEFAULT_DAILY_BRIEFING_TOPICS)
    focus_parts.append(f"watchlist names: {', '.join(watchlist[:8])}")
    if preferences.preferred_regions:
        focus_parts.append(f"preferred regions: {', '.join(preferences.preferred_regions[:5])}")

    return (
        "Generate today's personalized daily intelligence briefing in clean markdown. "
        "Use Tavily live web research as the primary current source, then use direct APIs and local stored data "
        "to verify or add context. Cover only the highest-signal developments across "
        f"{'; '.join(focus_parts)}. If user preferences are sparse, use those default topics to create a useful general brief. "
        "Structure the answer as ## Bottom Line, ## World News, ## Geopolitics, ## U.S. News, "
        "## AI And Major Tech, ## Markets And Watchlist, ## What To Watch, and ## Data Gaps. "
        "Use bullets, bold the key terms/tickers/companies/places/numbers, and label trend direction as strengthening, weakening, mixed, or unclear. "
        "Explain what changed, why it matters, what is uncertain, and what to watch next. "
        "Use source-backed evidence only and do not give buy, sell, or hold instructions."
    )


def generate_company_research(session: Session, request: CompanyResearchRequest) -> ReportResponse:
    now = datetime.now(UTC)
    tickers = normalize_symbols([request.ticker] if request.ticker else [])
    companies = [request.company.strip()] if request.company and request.company.strip() else []
    domains = request.domains or COMPANY_RESEARCH_DOMAINS
    subject = ", ".join([*tickers, *companies])
    query = request.user_query or (
        f"Generate a company research report for {subject}. Cover recent company-specific news or filings, "
        "business context, market and macro context, potential catalysts, key risks, and open questions. "
        "Use source-backed evidence only and do not give buy, sell, or hold instructions."
    )
    agent_request = AgentQueryRequest(
        user_query=query,
        intent="company_research",
        domains=domains,
        tickers=tickers,
        companies=companies,
        regions=request.regions,
        time_window=request.time_window,
        safety_level="investment_research",
    )
    agent_response = run_agent_query(agent_request, session)

    report = Report(
        report_type="company_research",
        status="generated",
        title=request.title or default_report_title(
            ReportCreateRequest(report_type="company_research", tickers=tickers, companies=companies),
            now,
        ),
        summary=build_report_summary(agent_response),
        body=agent_response.summary,
        domains=domains,
        tickers=tickers,
        companies=companies,
        as_of=now,
        confidence=agent_response.confidence,
        disclaimer_version="v1",
        guardrail_status=agent_response.guardrail.status,
        report_metadata={
            "user_query": query,
            "regions": request.regions,
            "time_window": request.time_window,
            "generation_stage": "company_research",
            "agent_request_id": agent_response.request_id,
            "agents_ran": agent_response.agents_ran,
            "requires_guardrail_review": agent_response.requires_guardrail_review,
            "follow_up_questions": agent_response.follow_up_questions,
            "risks": agent_response.risks,
            **build_panel_signal_metadata(session, "company_research", agent_response),
        },
    )
    session.add(report)
    session.flush()
    add_report_citations(session, report, agent_response.citations)
    session.commit()
    session.refresh(report)
    return get_report(session, report.id)


def generate_market_strategy(session: Session, request: MarketStrategyRequest) -> ReportResponse:
    now = datetime.now(UTC)
    tickers = normalize_symbols(request.tickers)
    domains = request.domains or MARKET_STRATEGY_DOMAINS
    query = request.user_query or (
        "Generate a market strategy research note using source-backed evidence. Include base, upside, and downside "
        "scenario framing, watch items for rates, credit, sectors, volatility, and macro releases, plus key risks. "
        "Do not provide direct buy, sell, or hold instructions."
    )
    agent_request = AgentQueryRequest(
        user_query=query,
        intent="market_research",
        domains=domains,
        tickers=tickers,
        regions=request.regions,
        time_window=request.time_window,
        safety_level="investment_research",
    )
    agent_response = run_agent_query(agent_request, session)

    report = Report(
        report_type="market_strategy",
        status="generated",
        title=request.title or default_report_title(
            ReportCreateRequest(report_type="market_strategy", tickers=tickers),
            now,
        ),
        summary=build_report_summary(agent_response),
        body=agent_response.summary,
        domains=domains,
        tickers=tickers,
        companies=[],
        as_of=now,
        confidence=agent_response.confidence,
        disclaimer_version="v1",
        guardrail_status=agent_response.guardrail.status,
        report_metadata={
            "user_query": query,
            "regions": request.regions,
            "time_window": request.time_window,
            "generation_stage": "market_strategy",
            "agent_request_id": agent_response.request_id,
            "agents_ran": agent_response.agents_ran,
            "requires_guardrail_review": agent_response.requires_guardrail_review,
            "follow_up_questions": agent_response.follow_up_questions,
            "risks": agent_response.risks,
            "scenario_sections_expected": ["base", "upside", "downside"],
            **build_panel_signal_metadata(session, "market_strategy", agent_response),
        },
    )
    session.add(report)
    session.flush()
    add_report_citations(session, report, agent_response.citations)
    session.commit()
    session.refresh(report)
    return get_report(session, report.id)


def generate_housing_report(session: Session, request: HousingReportRequest) -> ReportResponse:
    now = datetime.now(UTC)
    domains = request.domains or HOUSING_REPORT_DOMAINS
    query = request.user_query or (
        "Generate a housing market research report using source-backed evidence. Cover mortgage rates, "
        "affordability, home prices, supply and demand, construction, credit conditions, and key risks. "
        "State data recency and uncertainty clearly."
    )
    agent_request = AgentQueryRequest(
        user_query=query,
        intent="housing_macro_research",
        domains=domains,
        regions=request.regions,
        time_window=request.time_window,
        safety_level="investment_research",
    )
    agent_response = run_agent_query(agent_request, session)

    report = build_generated_report(
        report_type="housing",
        title=request.title or default_report_title(ReportCreateRequest(report_type="housing"), now),
        domains=domains,
        tickers=[],
        companies=[],
        as_of=now,
        agent_response=agent_response,
        metadata={
            "user_query": query,
            "regions": request.regions,
            "time_window": request.time_window,
            "generation_stage": "housing",
            "expected_sections": ["mortgage_rates", "affordability", "supply_demand", "risks"],
            **build_panel_signal_metadata(session, "housing", agent_response),
        },
    )
    session.add(report)
    session.flush()
    add_report_citations(session, report, agent_response.citations)
    session.commit()
    session.refresh(report)
    return get_report(session, report.id)


def generate_macro_report(session: Session, request: MacroReportRequest) -> ReportResponse:
    now = datetime.now(UTC)
    domains = request.domains or MACRO_REPORT_DOMAINS
    query = request.user_query or (
        "Generate a macroeconomic research report using source-backed evidence. Cover rates, labor, inflation "
        "or price-pressure context where available, policy signals, credit conditions, broad economic risks, "
        "and what to watch next. State data recency and uncertainty clearly."
    )
    agent_request = AgentQueryRequest(
        user_query=query,
        intent="housing_macro_research",
        domains=domains,
        regions=request.regions,
        time_window=request.time_window,
        safety_level="investment_research",
    )
    agent_response = run_agent_query(agent_request, session)

    report = build_generated_report(
        report_type="macro",
        title=request.title or default_report_title(ReportCreateRequest(report_type="macro"), now),
        domains=domains,
        tickers=[],
        companies=[],
        as_of=now,
        agent_response=agent_response,
        metadata={
            "user_query": query,
            "regions": request.regions,
            "time_window": request.time_window,
            "generation_stage": "macro",
            "expected_sections": ["rates", "labor", "policy", "credit", "risks"],
            **build_panel_signal_metadata(session, "macro", agent_response),
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
    statement = statement.where(Report.status != "archived")

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


def archive_report(session: Session, report_id: int) -> ReportResponse:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.status = "archived"
    session.commit()
    session.refresh(report)
    return get_report(session, report.id)


def regenerate_report(session: Session, report_id: int) -> ReportResponse:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    metadata = report.report_metadata or {}
    regions = list(metadata.get("regions") or [])
    time_window = metadata.get("time_window") or default_time_window(report.report_type)
    user_query = metadata.get("user_query")
    title = f"{report.title} Refresh"

    if report.report_type == "daily_briefing":
        return generate_daily_briefing(
            session,
            DailyBriefingRequest(
                title=title,
                domains=report.domains,
                regions=regions,
                time_window=time_window,
                user_query=user_query,
            ),
        )
    if report.report_type == "company_research":
        return generate_company_research(
            session,
            CompanyResearchRequest(
                title=title,
                ticker=(report.tickers or [None])[0],
                company=(report.companies or [None])[0],
                domains=report.domains,
                regions=regions,
                time_window=time_window,
                user_query=user_query,
            ),
        )
    if report.report_type == "market_strategy":
        return generate_market_strategy(
            session,
            MarketStrategyRequest(
                title=title,
                domains=report.domains,
                tickers=report.tickers,
                regions=regions,
                time_window=time_window,
                user_query=user_query,
            ),
        )
    if report.report_type == "housing":
        return generate_housing_report(
            session,
            HousingReportRequest(
                title=title,
                domains=report.domains,
                regions=regions,
                time_window=time_window,
                user_query=user_query,
            ),
        )
    if report.report_type == "macro":
        return generate_macro_report(
            session,
            MacroReportRequest(
                title=title,
                domains=report.domains,
                regions=regions,
                time_window=time_window,
                user_query=user_query,
            ),
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report type cannot be regenerated")


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


def build_generated_report(
    *,
    report_type: str,
    title: str,
    domains: list[str],
    tickers: list[str],
    companies: list[str],
    as_of: datetime,
    agent_response: AgentQueryResponse,
    metadata: dict,
) -> Report:
    report_metadata = {
        **metadata,
        "agent_request_id": agent_response.request_id,
        "agents_ran": agent_response.agents_ran,
        "requires_guardrail_review": agent_response.requires_guardrail_review,
        "follow_up_questions": agent_response.follow_up_questions,
        "risks": agent_response.risks,
    }
    return Report(
        report_type=report_type,
        status="generated",
        title=title,
        summary=build_report_summary(agent_response),
        body=agent_response.summary,
        domains=domains,
        tickers=tickers,
        companies=companies,
        as_of=as_of,
        confidence=agent_response.confidence,
        disclaimer_version="v1",
        guardrail_status=agent_response.guardrail.status,
        report_metadata=report_metadata,
    )


def build_panel_signal_metadata(
    session: Session,
    report_type: str,
    agent_response: AgentQueryResponse,
) -> dict[str, Any]:
    previous_report = latest_previous_report(session, report_type)
    signal_label = classify_signal(agent_response)
    change_label = classify_change(previous_report, agent_response.summary)
    source_count = len(agent_response.citations)

    return {
        "signal_label": signal_label,
        "change_label": change_label,
        "source_quality": source_quality_note(agent_response),
        "previous_report_id": previous_report.id if previous_report else None,
        "previous_report_as_of": format_datetime(previous_report.as_of) if previous_report else None,
        "citation_count": source_count,
    }


def latest_previous_report(session: Session, report_type: str) -> Report | None:
    return session.scalar(
        select(Report)
        .where(Report.report_type == report_type, Report.status == "generated")
        .order_by(desc(Report.as_of), desc(Report.id))
        .limit(1)
    )


def classify_signal(agent_response: AgentQueryResponse) -> str:
    source_count = len(agent_response.citations)
    summary = agent_response.summary.lower()

    if source_count == 0 and any(
        phrase in summary
        for phrase in (
            "no current",
            "no specific evidence",
            "does not include",
            "cannot determine",
            "could not find",
        )
    ):
        return "Noise"
    if source_count == 0 or agent_response.confidence == "low":
        return "Watch Later"
    if agent_response.confidence == "high" and source_count >= 3:
        return "High Signal"
    if agent_response.confidence == "medium" and source_count >= 5:
        return "High Signal"
    return "Developing"


def classify_change(previous_report: Report | None, current_text: str) -> str:
    if previous_report is None:
        return "New"

    previous_tokens = meaningful_tokens(previous_report.body)
    current_tokens = meaningful_tokens(current_text)
    if previous_tokens and current_tokens:
        overlap = len(previous_tokens & current_tokens) / max(len(current_tokens), 1)
        if overlap >= 0.86:
            return "No Meaningful Change"

    current_lower = current_text.lower()
    improving_count = sum(1 for term in IMPROVING_TERMS if term in current_lower)
    worsening_count = sum(1 for term in WORSENING_TERMS if term in current_lower)
    if worsening_count > improving_count:
        return "Worsening"
    if improving_count > worsening_count:
        return "Improving"
    return "Mixed"


def meaningful_tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 4}


def source_quality_note(agent_response: AgentQueryResponse) -> str:
    source_count = len(agent_response.citations)
    if agent_response.confidence == "high" and source_count >= 3:
        return "Strong: multiple current sources support the answer."
    if source_count > 0:
        return "Useful but developing: current sources are available, but the picture may still move."
    return "Thin: source coverage is limited, so treat this as a watch item."


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


def default_time_window(report_type: str) -> str:
    if report_type == "daily_briefing":
        return "week"
    if report_type in {"housing", "macro"}:
        return "quarter"
    return "month"


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
