from app.schemas.agent import AgentContext
from app.schemas.research_workflow import EvidenceNeed, ResearchWorkflowPlan, ResearchWorkflowStep


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


def build_research_workflow_plan(context: AgentContext, specialist_agents: list[str]) -> ResearchWorkflowPlan:
    retrieval_priority = retrieval_priority_for_context(context)
    evidence_needs = build_evidence_needs(context, retrieval_priority)
    steps = build_workflow_steps(retrieval_priority)

    return ResearchWorkflowPlan(
        request_id=context.request_id,
        user_query=context.user_query,
        intent=context.intent,
        domains=context.domains,
        tickers=context.tickers,
        companies=context.companies,
        regions=context.regions,
        time_window=context.time_window,
        answer_style=answer_style_for_context(context),
        retrieval_priority=retrieval_priority,
        evidence_needs=evidence_needs,
        specialist_agents=specialist_agents,
        steps=steps,
        manual_requirements=[],
    )


def retrieval_priority_for_context(context: AgentContext) -> list[str]:
    if should_prioritize_live_web(context):
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


def build_evidence_needs(context: AgentContext, retrieval_priority: list[str]) -> list[EvidenceNeed]:
    queries = build_search_queries(context)
    source_ids = source_ids_for_context(context)
    needs: list[EvidenceNeed] = []

    for channel in retrieval_priority:
        if channel == "live_web":
            needs.append(
                EvidenceNeed(
                    channel="live_web",
                    purpose="Find current credible sources and citations for the user's question.",
                    search_queries=queries,
                    required=should_prioritize_live_web(context),
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


def build_search_queries(context: AgentContext) -> list[str]:
    parts = [context.user_query]
    if context.regions:
        parts.append(" ".join(context.regions[:3]))
    if context.tickers:
        parts.append(" ".join(context.tickers[:5]))
    if context.companies:
        parts.append(" ".join(context.companies[:5]))
    return [" ".join(part for part in parts if part).strip()]


def source_ids_for_context(context: AgentContext) -> list[str]:
    if context.source_ids:
        return context.source_ids

    source_ids: list[str] = []
    for domain in context.domains:
        source_ids.extend(DOMAIN_SOURCE_HINTS.get(domain, []))
    if context.tickers or context.companies:
        source_ids.extend(DOMAIN_SOURCE_HINTS["Companies and Earnings"])
    if context.regions:
        source_ids.extend(DOMAIN_SOURCE_HINTS["Housing and Real Estate"])
    if not source_ids:
        source_ids.extend(["bbc-news-rss", "newsapi", "gdelt-cloud", "alpha-vantage"])
    return dedupe(source_ids)


def answer_style_for_context(context: AgentContext) -> str:
    text = searchable_text(context)
    if any(term in text for term in ("deep dive", "detailed", "thorough")):
        return "deep_dive"
    if any(term in text for term in ("quick", "brief", "summary")):
        return "brief"
    return "standard"


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
