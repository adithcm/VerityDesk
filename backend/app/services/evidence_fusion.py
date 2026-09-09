from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Report
from app.schemas.agent import AgentCitation, AgentContext
from app.schemas.evidence_packet import (
    EvidencePacket,
    EvidencePacketItem,
    EvidencePacketQuality,
    EvidencePacketSourceKind,
    EvidenceRetrievalStatus,
)
from app.schemas.live_web import LiveWebSearchRequest, LiveWebSearchResponse
from app.schemas.research_workflow import EvidenceNeed, ResearchWorkflowPlan
from app.services.live_web_research import run_live_web_search
from app.services.research_evidence import (
    ArticleEvidence,
    EconomicObservationEvidence,
    EvidenceQuery,
    ResearchEvidenceRepository,
)


DIRECT_API_SOURCE_IDS = {
    "alpha-vantage",
    "census-economic-indicators",
    "finnhub",
    "fred-api",
    "freddie-mac-pmms",
    "fhfa-hpi",
    "gdelt-cloud",
    "newsapi",
    "sec-data-apis",
}

QUALITY_SCORE = {
    "primary": 45,
    "reputable": 35,
    "provider": 30,
    "internal": 25,
    "discovery": 15,
}

CHANNEL_SCORE = {
    "live_web": 100,
    "direct_api": 80,
    "local_cache": 55,
    "saved_report": 45,
}


def build_evidence_packet(
    *,
    context: AgentContext,
    plan: ResearchWorkflowPlan,
    session: Session,
    max_items: int = 16,
) -> EvidencePacket:
    repository = ResearchEvidenceRepository(session)
    items: list[EvidencePacketItem] = []
    statuses: list[EvidenceRetrievalStatus] = []

    for need in plan.evidence_needs:
        if need.channel == "live_web":
            live_results = collect_live_web_evidence(need)
            statuses.extend(
                EvidenceRetrievalStatus(
                    channel="live_web",
                    status=response.status,
                    query=response.query,
                    message=response.message,
                )
                for response in live_results
            )
            for response in live_results:
                items.extend(live_web_response_to_items(response))
        elif need.channel == "direct_api":
            direct_items = collect_repository_items(context, plan, need, repository, source_kind="direct_api")
            items.extend(direct_items)
            statuses.append(
                EvidenceRetrievalStatus(
                    channel="direct_api",
                    status="success" if direct_items else "skipped",
                    message=f"Found {len(direct_items)} API-backed evidence items."
                    if direct_items
                    else "No matching API-backed evidence was available in the local store.",
                )
            )
        elif need.channel == "local_cache":
            local_items = collect_repository_items(context, plan, need, repository, source_kind="local_cache")
            report_items = collect_saved_report_items(context, session)
            combined_count = len(local_items) + len(report_items)
            items.extend([*local_items, *report_items])
            statuses.append(
                EvidenceRetrievalStatus(
                    channel="local_cache",
                    status="success" if combined_count else "skipped",
                    message=f"Found {combined_count} local evidence items."
                    if combined_count
                    else "No matching cached articles, observations, or saved reports were available.",
                )
            )

    ranked_items = rank_and_dedupe_items(items)[:max_items]
    return EvidencePacket(
        request_id=context.request_id,
        query=context.user_query,
        items=ranked_items,
        citations=dedupe_citations([item.citation for item in ranked_items if item.citation is not None]),
        retrieval_statuses=statuses,
    )


def collect_live_web_evidence(need: EvidenceNeed) -> list[LiveWebSearchResponse]:
    queries = need.search_queries[:1] or []
    if not queries:
        return [
            LiveWebSearchResponse(
                provider="tavily",
                status="skipped",
                query="",
                message="No live web search query was generated.",
            )
        ]

    return [
        run_live_web_search(
            LiveWebSearchRequest(
                query=query,
                max_results=5,
            )
        )
        for query in queries
    ]


def live_web_response_to_items(response: LiveWebSearchResponse) -> list[EvidencePacketItem]:
    if response.status != "success":
        return []

    return [
        EvidencePacketItem(
            source_kind="live_web",
            source_id="tavily",
            source_name="Tavily Live Web",
            title=result.title,
            url=result.url,
            publisher=result.publisher,
            published_at=result.published_at,
            retrieved_at=result.retrieved_at,
            scope="web",
            summary=result.excerpt,
            source_quality=result.source_quality,
            relevance_score=result.relevance_score,
            citation=AgentCitation(
                source_id="tavily",
                title=result.citation.title,
                url=result.citation.url,
                publisher=result.citation.publisher,
                published_at=result.citation.published_at,
                retrieved_at=result.citation.retrieved_at,
                supports_claim=result.citation.supports_claim,
            ),
            metadata={"provider": response.provider, "query": response.query},
        )
        for result in response.results
    ]


def collect_repository_items(
    context: AgentContext,
    plan: ResearchWorkflowPlan,
    need: EvidenceNeed,
    repository: ResearchEvidenceRepository,
    *,
    source_kind: EvidencePacketSourceKind,
) -> list[EvidencePacketItem]:
    source_ids = filter_source_ids_for_kind(need.source_ids or context.source_ids, source_kind)
    evidence_query = EvidenceQuery(
        domains=plan.domains,
        source_ids=source_ids,
        tickers=plan.tickers,
        companies=plan.companies,
        regions=plan.regions,
        series_ids=series_ids_for_context(context, plan),
        time_window=context.time_window or plan.time_window,
        limit=8,
    )
    articles = repository.latest_articles(evidence_query)
    observations = repository.economic_observations(evidence_query)
    if source_kind == "direct_api":
        articles = [article for article in articles if article.source_id in DIRECT_API_SOURCE_IDS]
        observations = [observation for observation in observations if observation.source_id in DIRECT_API_SOURCE_IDS]
    else:
        articles = [article for article in articles if article.source_id not in DIRECT_API_SOURCE_IDS]
        observations = [observation for observation in observations if observation.source_id not in DIRECT_API_SOURCE_IDS]

    return [
        *[article_to_item(article, source_kind) for article in articles],
        *[observation_to_item(observation, source_kind) for observation in observations],
    ]


def filter_source_ids_for_kind(source_ids: list[str], source_kind: EvidencePacketSourceKind) -> list[str]:
    if source_kind == "direct_api":
        selected = [source_id for source_id in source_ids if source_id in DIRECT_API_SOURCE_IDS]
        return selected or list(source_ids)
    return [source_id for source_id in source_ids if source_id not in DIRECT_API_SOURCE_IDS]


def series_ids_for_context(context: AgentContext, plan: ResearchWorkflowPlan) -> list[str]:
    text = f"{context.user_query} {' '.join(plan.domains)} {' '.join(plan.regions)}".lower()
    user_text = context.user_query.lower()
    has_housing_terms = any(term in text for term in ("housing", "home", "mortgage", "real estate"))
    has_stock_terms = any(
        term in text
        for term in (
            "stocks",
            "stock",
            "equity",
            "equities",
            "s&p",
            "sp500",
            "nasdaq",
            "dow",
            "ticker",
            "watchlist",
            "earnings",
            "shares",
        )
    ) or bool(plan.tickers or plan.companies)
    has_user_stock_terms = any(
        term in user_text
        for term in (
            "market",
            "stocks",
            "stock",
            "equity",
            "equities",
            "s&p",
            "sp500",
            "nasdaq",
            "dow",
            "ticker",
            "watchlist",
            "earnings",
            "shares",
        )
    ) or bool(plan.tickers or plan.companies)
    series_ids: list[str] = []
    if has_housing_terms:
        series_ids.extend(["MORTGAGE30US", "FREDDIE_PMMS:*", "FHFA_HPI:*", "CENSUS_EITS:MHS:*", "CENSUS_EITS:RESSALES:*"])
    if any(term in text for term in ("market", "rate", "rates", "yield", "stocks", "s&p", "sp500")):
        series_ids.extend(["FEDFUNDS", "MORTGAGE30US"])
        if has_stock_terms and has_user_stock_terms and not (has_housing_terms and not bool(plan.tickers or plan.companies)):
            series_ids.extend(["ALPHA_VANTAGE:QUOTE:*", "FINNHUB:QUOTE:*"])
    if any(term in text for term in ("macro", "economy", "inflation", "jobs", "labor", "unemployment")):
        series_ids.extend(["FEDFUNDS", "UNRATE"])
    return dedupe_strings(series_ids)


def article_to_item(article: ArticleEvidence, source_kind: EvidencePacketSourceKind) -> EvidencePacketItem:
    citation = AgentCitation(
        source_id=article.source_id,
        title=article.citation.title,
        url=article.citation.url,
        publisher=article.publisher or article.source_name,
        published_at=article.published_at,
        retrieved_at=article.retrieved_at,
        supports_claim=article.citation.supports_claim,
    )
    return EvidencePacketItem(
        source_kind=source_kind,
        source_id=article.source_id,
        source_name=article.source_name,
        title=article.title,
        url=article.url,
        publisher=article.publisher or article.source_name,
        published_at=article.published_at,
        retrieved_at=article.retrieved_at,
        scope=scope_for_article(article),
        summary=article.summary or article.excerpt or "Article metadata is available, but no summary was stored.",
        source_quality=quality_for_source_id(article.source_id),
        relevance_score=article.relevance_score,
        citation=citation,
        metadata={"domains": ", ".join(article.domains), "kind": "article"},
    )


def observation_to_item(observation: EconomicObservationEvidence, source_kind: EvidencePacketSourceKind) -> EvidencePacketItem:
    citation = AgentCitation(
        source_id=observation.source_id,
        title=observation.citation.title,
        publisher=observation.source_name,
        published_at=observation.released_at,
        retrieved_at=observation.retrieved_at,
        supports_claim=observation.citation.supports_claim,
    )
    region = f" for {observation.region}" if observation.region else ""
    unit = f" {observation.unit}" if observation.unit else ""
    return EvidencePacketItem(
        source_kind=source_kind,
        source_id=observation.source_id,
        source_name=observation.source_name,
        title=observation.display_name,
        publisher=observation.source_name,
        published_at=observation.released_at,
        retrieved_at=observation.retrieved_at,
        scope=observation.region or "US/national",
        summary=(
            f"{observation.display_name} was {observation.value}{unit}{region} "
            f"for {observation.period}. {observation.description}"
        ),
        source_quality=quality_for_source_id(observation.source_id),
        relevance_score=observation.relevance_score,
        citation=citation,
        metadata={"series_id": observation.series_id, "period": observation.period, "kind": "economic_observation"},
    )


def collect_saved_report_items(context: AgentContext, session: Session) -> list[EvidencePacketItem]:
    reports = session.scalars(
        select(Report)
        .order_by(desc(Report.as_of), desc(Report.created_at), desc(Report.id))
        .limit(10)
    ).all()
    query_terms = normalized_query_terms(context)
    items: list[EvidencePacketItem] = []
    for report in reports:
        if query_terms and not report_matches(report, query_terms):
            continue
        items.append(
            EvidencePacketItem(
                source_kind="saved_report",
                source_id=f"report:{report.id}",
                source_name="Saved report",
                title=report.title,
                published_at=format_datetime(report.as_of),
                retrieved_at=format_datetime(report.created_at),
                scope=", ".join([*report.domains, *report.tickers, *report.companies]) or "saved research",
                summary=report.summary or report.body[:500],
                source_quality="internal",
                relevance_score=2,
                metadata={"report_id": report.id, "report_type": report.report_type},
            )
        )
    return items[:3]


def normalized_query_terms(context: AgentContext) -> set[str]:
    terms = [*context.domains, *context.tickers, *context.companies, *context.regions]
    return {term.strip().lower() for term in terms if term.strip()}


def report_matches(report: Report, terms: set[str]) -> bool:
    haystack = " ".join(
        [
            report.title,
            report.summary or "",
            " ".join(report.domains),
            " ".join(report.tickers),
            " ".join(report.companies),
        ]
    ).lower()
    return any(term in haystack for term in terms)


def rank_and_dedupe_items(items: list[EvidencePacketItem]) -> list[EvidencePacketItem]:
    deduped: dict[str, EvidencePacketItem] = {}
    for item in items:
        ranked = item.model_copy(update={"rank_score": rank_score(item)})
        key = item_key(ranked)
        existing = deduped.get(key)
        if existing is None or ranked.rank_score > existing.rank_score:
            deduped[key] = ranked
    return sorted(deduped.values(), key=lambda item: item.rank_score, reverse=True)


def rank_score(item: EvidencePacketItem) -> float:
    return (
        CHANNEL_SCORE[item.source_kind]
        + QUALITY_SCORE[item.source_quality]
        + min(item.relevance_score, 10)
        + recency_score(item.published_at or item.retrieved_at)
    )


def recency_score(value: str | None) -> int:
    if value is None:
        return 0
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    age_days = max((datetime.now(observed.tzinfo) - observed).days, 0)
    if age_days <= 1:
        return 10
    if age_days <= 7:
        return 7
    if age_days <= 30:
        return 4
    return 1


def item_key(item: EvidencePacketItem) -> str:
    if item.url:
        return item.url.lower()
    return f"{item.source_kind}:{item.source_id}:{item.title}:{item.published_at}".lower()


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


def scope_for_article(article: ArticleEvidence) -> str:
    if article.regions:
        return ", ".join(article.regions)
    if article.tickers:
        return ", ".join(article.tickers)
    if article.companies:
        return ", ".join(article.companies)
    return ", ".join(article.domains) or "news"


def quality_for_source_id(source_id: str) -> EvidencePacketQuality:
    if source_id in {"fred-api", "census-economic-indicators", "fhfa-hpi", "sec-data-apis"}:
        return "primary"
    if source_id in {"alpha-vantage", "finnhub", "freddie-mac-pmms", "newsapi", "gdelt-cloud"}:
        return "provider"
    if source_id in {"bbc-news-rss", "sec-edgar-rss"}:
        return "reputable"
    return "internal"


def format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
