import re

from app.schemas.agent import AgentContext
from app.schemas.research_workflow import (
    AnswerStyle,
    EvidenceNeed,
    QueryUnderstanding,
    ResearchWorkflowPlan,
    ResearchWorkflowStep,
)
from app.services.region_normalization import expand_regions, infer_regions_from_text


WEB_FIRST_KEYWORDS = {
    "today",
    "latest",
    "current",
    "right now",
    "this week",
    "what is happening",
    "what's happening",
    "news",
}

DOMAIN_SOURCE_HINTS = {
    "Companies and Earnings": ["sec-data-apis", "sec-edgar-rss", "alpha-vantage", "finnhub", "newsapi"],
    "Housing and Real Estate": ["fhfa-hpi", "freddie-mac-pmms", "fred-api", "census-economic-indicators", "newsapi"],
    "Markets and Rates": ["fred-api", "freddie-mac-pmms", "alpha-vantage", "finnhub", "newsapi"],
    "Technology and AI": ["newsapi", "alpha-vantage"],
    "World and Geopolitics": ["bbc-news-rss", "newsapi", "gdelt-cloud"],
    "U.S. Economy and Policy": ["fred-api", "census-economic-indicators", "newsapi"],
}

TOPIC_KEYWORDS = {
    "housing": ("housing", "mortgage", "real estate", "home price", "rent", "affordability", "inventory"),
    "markets": ("market", "stocks", "s&p", "sp500", "nasdaq", "dow", "yield", "bond", "rates"),
    "macro": ("macro", "economy", "inflation", "jobs", "labor", "unemployment", "fed", "gdp", "consumer"),
    "company": ("company", "earnings", "filing", "revenue", "guidance", "sec"),
    "world_news": ("world", "geopolitics", "war", "election", "policy", "tariff"),
    "technology": ("technology", "tech", "ai", "chips", "semiconductor", "software"),
    "energy": ("oil", "gas", "energy", "commodity", "commodities", "shipping"),
    "banking": ("bank", "credit", "loan", "delinquency", "default"),
}

TOPIC_DOMAINS = {
    "housing": ["Housing and Real Estate", "Markets and Rates", "U.S. Economy and Policy"],
    "markets": ["Markets and Rates"],
    "macro": ["U.S. Economy and Policy", "Consumer and Labor", "Markets and Rates"],
    "company": ["Companies and Earnings"],
    "world_news": ["World and Geopolitics"],
    "technology": ["Technology and AI", "Companies and Earnings"],
    "energy": ["Commodities and Energy", "World and Geopolitics"],
    "banking": ["Banking and Credit", "Markets and Rates"],
}

SECTOR_KEYWORDS = {
    "Technology": ("technology", "tech", "ai", "software", "chips", "semiconductor"),
    "Energy": ("energy", "oil", "gas", "commodities"),
    "Financials": ("bank", "banks", "financials", "credit", "lending"),
    "Real Estate": ("housing", "real estate", "mortgage", "homebuilder", "reit"),
    "Consumer": ("consumer", "retail", "spending", "jobs"),
    "Healthcare": ("healthcare", "pharma", "biotech", "medical"),
}

COMPANY_ALIASES = {
    "apple": ("Apple", "AAPL"),
    "microsoft": ("Microsoft", "MSFT"),
    "nvidia": ("Nvidia", "NVDA"),
    "amazon": ("Amazon", "AMZN"),
    "alphabet": ("Alphabet", "GOOGL"),
    "google": ("Alphabet", "GOOGL"),
    "meta": ("Meta", "META"),
    "tesla": ("Tesla", "TSLA"),
}

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")
IGNORED_TICKERS = {"A", "I", "US", "USA", "UK", "EU", "AI", "GDP", "CPI", "AZ", "CA", "NY", "TX", "DC"}


def build_research_workflow_plan(context: AgentContext, specialist_agents: list[str]) -> ResearchWorkflowPlan:
    understanding = understand_query(context)
    retrieval_priority = retrieval_priority_for_context(context, understanding)
    evidence_needs = build_evidence_needs(context, understanding, retrieval_priority)
    steps = build_workflow_steps(retrieval_priority)

    return ResearchWorkflowPlan(
        request_id=context.request_id,
        user_query=context.user_query,
        intent=understanding.inferred_intent,
        domains=understanding.domains,
        tickers=understanding.tickers,
        companies=understanding.companies,
        regions=understanding.regions,
        time_window=understanding.time_window,
        answer_style=understanding.answer_style,
        query_understanding=understanding,
        requires_live_web=understanding.requires_live_web,
        retrieval_priority=retrieval_priority,
        evidence_needs=evidence_needs,
        specialist_agents=specialist_agents,
        steps=steps,
        manual_requirements=[],
    )


def understand_query(context: AgentContext) -> QueryUnderstanding:
    text = searchable_text(context)
    topics = infer_topics(text)
    regions = expand_regions([*context.regions, *infer_regions_from_text(context.user_query)])
    company_matches = infer_companies_and_tickers(text)
    companies = dedupe([*context.companies, *[company for company, _ticker in company_matches]])
    tickers = dedupe([*context.tickers, *infer_tickers(context.user_query), *[ticker for _company, ticker in company_matches]])
    sectors = infer_sectors(text)
    time_window = context.time_window or infer_time_window(text)
    answer_style = answer_style_for_text(text)
    freshness_need = freshness_need_for_text(text, time_window)
    inferred_intent = infer_intent(context, topics, tickers, companies, regions)
    domains = dedupe([*context.domains, *domains_for_topics(topics), *domains_for_entities(tickers, companies, regions)])
    requires_live_web = should_require_live_web(
        context=context,
        topics=topics,
        regions=regions,
        time_window=time_window,
        freshness_need=freshness_need,
    )

    return QueryUnderstanding(
        inferred_intent=inferred_intent,
        topics=topics,
        domains=domains,
        tickers=tickers,
        companies=companies,
        regions=regions,
        sectors=sectors,
        time_window=time_window,
        freshness_need=freshness_need,
        answer_style=answer_style,
        requires_live_web=requires_live_web,
        reasoning=build_understanding_reasoning(
            topics=topics,
            regions=regions,
            tickers=tickers,
            companies=companies,
            freshness_need=freshness_need,
            requires_live_web=requires_live_web,
        ),
    )


def retrieval_priority_for_context(context: AgentContext, understanding: QueryUnderstanding | None = None) -> list[str]:
    if (understanding and understanding.requires_live_web) or should_prioritize_live_web(context):
        return ["live_web", "direct_api", "local_cache"]
    return ["direct_api", "local_cache", "live_web"]


def should_prioritize_live_web(context: AgentContext) -> bool:
    text = searchable_text(context)
    return bool(
        context.intent in {"daily_briefing", "general_research"}
        or any(keyword in text for keyword in WEB_FIRST_KEYWORDS)
        or context.regions
        or not context.source_ids
    )


def build_evidence_needs(
    context: AgentContext,
    understanding: QueryUnderstanding,
    retrieval_priority: list[str],
) -> list[EvidenceNeed]:
    queries = build_search_queries(context, understanding)
    source_ids = source_ids_for_understanding(context, understanding)
    needs: list[EvidenceNeed] = []

    for channel in retrieval_priority:
        if channel == "live_web":
            needs.append(
                EvidenceNeed(
                    channel="live_web",
                    purpose="Find current credible sources and citations for the user's question.",
                    search_queries=queries,
                    required=understanding.requires_live_web,
                )
            )
        elif channel == "direct_api":
            needs.append(
                EvidenceNeed(
                    channel="direct_api",
                    purpose="Retrieve official or provider-backed structured data to verify and ground the answer.",
                    source_ids=source_ids,
                    search_queries=queries,
                    required=True,
                )
            )
        else:
            needs.append(
                EvidenceNeed(
                    channel="local_cache",
                    purpose="Reuse recently ingested articles, observations, source health, and saved reports.",
                    source_ids=source_ids,
                    search_queries=queries,
                    required=False,
                )
            )

    return needs


def build_workflow_steps(retrieval_priority: list[str]) -> list[ResearchWorkflowStep]:
    steps = [
        ResearchWorkflowStep(
            step_id="understand-query",
            step_type="query_understanding",
            label="Understand the question",
        ),
        ResearchWorkflowStep(
            step_id="plan-research",
            step_type="research_planning",
            label="Plan retrieval and agents",
            depends_on=["understand-query"],
        ),
    ]
    step_id_by_channel = {
        "live_web": "search-live-web",
        "direct_api": "fetch-direct-apis",
        "local_cache": "read-local-cache",
    }
    step_type_by_channel = {
        "live_web": "live_web_research",
        "direct_api": "direct_api_lookup",
        "local_cache": "local_evidence_lookup",
    }
    label_by_channel = {
        "live_web": "Search credible live web sources",
        "direct_api": "Fetch direct API evidence",
        "local_cache": "Read local cached evidence",
    }

    for channel in retrieval_priority:
        steps.append(
            ResearchWorkflowStep(
                step_id=step_id_by_channel[channel],
                step_type=step_type_by_channel[channel],
                label=label_by_channel[channel],
                depends_on=["plan-research"],
            )
        )

    retrieval_steps = [step_id_by_channel[channel] for channel in retrieval_priority]
    steps.extend(
        [
            ResearchWorkflowStep(
                step_id="fuse-evidence",
                step_type="evidence_fusion",
                label="Rank and reconcile evidence",
                depends_on=retrieval_steps,
            ),
            ResearchWorkflowStep(
                step_id="run-specialists",
                step_type="specialist_analysis",
                label="Run specialist agents",
                depends_on=["fuse-evidence"],
            ),
            ResearchWorkflowStep(
                step_id="synthesize-answer",
                step_type="answer_synthesis",
                label="Write clean answer",
                depends_on=["run-specialists"],
            ),
            ResearchWorkflowStep(
                step_id="check-citations-guardrails",
                step_type="citation_guardrail",
                label="Check citations and financial guardrails",
                depends_on=["synthesize-answer"],
            ),
        ]
    )
    return steps


def build_search_queries(context: AgentContext, understanding: QueryUnderstanding) -> list[str]:
    focused_user_query = live_search_query_text(context.user_query)
    primary_parts = [
        focused_user_query,
        " ".join(understanding.regions[:2]),
        " ".join(understanding.companies[:3]) if "company" in understanding.topics else "",
        " ".join(understanding.tickers[:5]) if "company" in understanding.topics else "",
    ]
    queries = [" ".join(part for part in primary_parts if part).strip()]

    if understanding.topics:
        topic_parts = [
            " ".join(understanding.topics[:3]),
            " ".join(understanding.regions[:2]),
            "latest credible sources",
        ]
        queries.append(" ".join(part for part in topic_parts if part).strip())

    if understanding.companies or understanding.tickers:
        company_parts = [
            " ".join([*understanding.companies[:3], *understanding.tickers[:5]]),
            "earnings filings investor relations latest news",
        ]
        queries.append(" ".join(part for part in company_parts if part).strip())

    return dedupe(queries)


def live_search_query_text(user_query: str) -> str:
    first_section = user_query.split("Use this saved user context:", 1)[0]
    first_line = next((line.strip() for line in first_section.splitlines() if line.strip()), first_section.strip())
    return first_line or user_query.strip()


def source_ids_for_context(context: AgentContext) -> list[str]:
    return source_ids_for_understanding(context, understand_query(context))


def source_ids_for_understanding(context: AgentContext, understanding: QueryUnderstanding) -> list[str]:
    if context.source_ids:
        return context.source_ids

    source_ids: list[str] = []
    for domain in understanding.domains:
        source_ids.extend(DOMAIN_SOURCE_HINTS.get(domain, []))
    if understanding.tickers or understanding.companies:
        source_ids.extend(DOMAIN_SOURCE_HINTS["Companies and Earnings"])
    if understanding.regions:
        source_ids.extend(DOMAIN_SOURCE_HINTS["Housing and Real Estate"])
    if not source_ids:
        source_ids.extend(["bbc-news-rss", "newsapi", "gdelt-cloud", "alpha-vantage"])
    return dedupe(source_ids)


def build_legacy_search_queries(context: AgentContext) -> list[str]:
    parts = [context.user_query]
    if context.regions:
        parts.append(" ".join(context.regions[:3]))
    if context.tickers:
        parts.append(" ".join(context.tickers[:5]))
    if context.companies:
        parts.append(" ".join(context.companies[:5]))
    return [" ".join(part for part in parts if part).strip()]


def answer_style_for_context(context: AgentContext) -> str:
    return answer_style_for_text(searchable_text(context))


def infer_topics(text: str) -> list[str]:
    return [
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(text_has_keyword(text, keyword) for keyword in keywords)
    ]


def domains_for_topics(topics: list[str]) -> list[str]:
    domains: list[str] = []
    for topic in topics:
        domains.extend(TOPIC_DOMAINS.get(topic, []))
    return domains


def domains_for_entities(tickers: list[str], companies: list[str], regions: list[str]) -> list[str]:
    domains: list[str] = []
    if tickers or companies:
        domains.extend(TOPIC_DOMAINS["company"])
    if regions:
        domains.extend(TOPIC_DOMAINS["housing"])
    return domains


def infer_tickers(query: str) -> list[str]:
    return [
        match.group(0)
        for match in TICKER_PATTERN.finditer(query)
        if match.group(0) not in IGNORED_TICKERS
    ]


def infer_companies_and_tickers(text: str) -> list[tuple[str, str]]:
    return [
        company
        for alias, company in COMPANY_ALIASES.items()
        if re.search(rf"\b{re.escape(alias)}\b", text)
    ]


def infer_sectors(text: str) -> list[str]:
    return [
        sector
        for sector, keywords in SECTOR_KEYWORDS.items()
        if any(text_has_keyword(text, keyword) for keyword in keywords)
    ]


def infer_time_window(text: str) -> str | None:
    if any(term in text for term in ("today", "right now", "current", "latest")):
        return "today"
    if "this week" in text or "week" in text:
        return "week"
    if "this month" in text or "month" in text:
        return "month"
    if "quarter" in text or "q1" in text or "q2" in text or "q3" in text or "q4" in text:
        return "quarter"
    if "year" in text or "ytd" in text:
        return "year"
    return None


def answer_style_for_text(text: str) -> AnswerStyle:
    if any(term in text for term in ("deep dive", "detailed", "thorough")):
        return "deep_dive"
    if any(term in text for term in ("quick", "brief", "summary")):
        return "brief"
    return "standard"


def freshness_need_for_text(text: str, time_window: str | None) -> str:
    if time_window in {"today", "week"} or any(keyword in text for keyword in WEB_FIRST_KEYWORDS):
        return "current"
    if time_window in {"year", "historical"} or any(term in text for term in ("historical", "history", "trend over")):
        return "historical"
    return "recent"


def infer_intent(
    context: AgentContext,
    topics: list[str],
    tickers: list[str],
    companies: list[str],
    regions: list[str],
) -> str:
    if context.intent != "general_research":
        return context.intent
    if "housing" in topics or ("macro" in topics and regions):
        return "housing_macro_research"
    if tickers or companies or "company" in topics:
        return "company_research"
    if "markets" in topics or "macro" in topics:
        return "market_research"
    if "world_news" in topics:
        return "daily_briefing"
    return context.intent


def should_require_live_web(
    *,
    context: AgentContext,
    topics: list[str],
    regions: list[str],
    time_window: str | None,
    freshness_need: str,
) -> bool:
    text = searchable_text(context)
    return bool(
        freshness_need == "current"
        or time_window in {"today", "week"}
        or regions
        or "world_news" in topics
        or "news" in text
        or context.intent in {"daily_briefing", "general_research"}
    )


def text_has_keyword(text: str, keyword: str) -> bool:
    if len(keyword) <= 3 and keyword.isalnum():
        return bool(re.search(rf"\b{re.escape(keyword)}\b", text))
    return keyword in text


def build_understanding_reasoning(
    *,
    topics: list[str],
    regions: list[str],
    tickers: list[str],
    companies: list[str],
    freshness_need: str,
    requires_live_web: bool,
) -> str:
    signals: list[str] = []
    if topics:
        signals.append(f"topics: {', '.join(topics)}")
    if regions:
        signals.append(f"regions: {', '.join(regions[:4])}")
    if tickers:
        signals.append(f"tickers: {', '.join(tickers)}")
    if companies:
        signals.append(f"companies: {', '.join(companies)}")
    signals.append(f"freshness need: {freshness_need}")
    signals.append("live web required" if requires_live_web else "direct/local evidence can lead")
    return "; ".join(signals)


def searchable_text(context: AgentContext) -> str:
    return " ".join(
        [
            context.user_query,
            context.intent,
            *context.domains,
            *context.tickers,
            *context.companies,
            *context.regions,
            context.time_window or "",
        ]
    ).lower()


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped
