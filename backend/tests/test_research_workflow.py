from app.schemas.agent import AgentContext
from app.services.research_workflow import build_research_workflow_plan, understand_query


def build_context(**overrides) -> AgentContext:
    data = {
        "request_id": "request-1",
        "user_query": "What is happening with housing in Arizona right now?",
        "intent": "housing_macro_research",
        "domains": ["Housing and Real Estate"],
        "regions": ["Arizona"],
    }
    data.update(overrides)
    return AgentContext(**data)


def test_research_workflow_plan_prioritizes_live_web_for_current_regional_question() -> None:
    context = build_context()

    plan = build_research_workflow_plan(context, ["HousingAgent", "MarketAgent"])

    assert plan.request_id == "request-1"
    assert plan.requires_live_web is True
    assert plan.retrieval_priority == ["live_web", "direct_api", "local_cache"]
    assert plan.specialist_agents == ["HousingAgent", "MarketAgent"]
    assert plan.manual_requirements == []
    assert plan.query_understanding is not None
    assert plan.query_understanding.topics == ["housing", "macro"]
    assert plan.query_understanding.freshness_need == "current"
    assert plan.evidence_needs[0].channel == "live_web"
    assert plan.evidence_needs[0].required is True
    assert "credible sources" in plan.evidence_needs[0].purpose
    assert "Arizona" in plan.evidence_needs[0].search_queries[0]


def test_research_workflow_plan_uses_direct_api_support_for_structured_query() -> None:
    context = build_context(
        user_query="Show me a detailed mortgage rate and FHFA view for Arizona",
        time_window="quarter",
    )

    plan = build_research_workflow_plan(context, ["HousingAgent"])

    direct_api_need = next(need for need in plan.evidence_needs if need.channel == "direct_api")
    assert plan.answer_style == "deep_dive"
    assert "fhfa-hpi" in direct_api_need.source_ids
    assert "freddie-mac-pmms" in direct_api_need.source_ids
    assert "census-economic-indicators" in direct_api_need.source_ids


def test_research_workflow_steps_keep_debug_trace_hidden_from_primary_ui() -> None:
    plan = build_research_workflow_plan(build_context(), ["HousingAgent"])

    step_ids = [step.step_id for step in plan.steps]

    assert step_ids == [
        "understand-query",
        "plan-research",
        "search-live-web",
        "fetch-direct-apis",
        "read-local-cache",
        "fuse-evidence",
        "run-specialists",
        "synthesize-answer",
        "check-citations-guardrails",
    ]
    assert all(step.hidden_from_primary_ui for step in plan.steps)
    assert plan.steps[-1].depends_on == ["synthesize-answer"]


def test_research_workflow_plan_respects_explicit_source_ids() -> None:
    context = build_context(source_ids=["fred-api"], domains=[])

    plan = build_research_workflow_plan(context, ["MacroAgent"])

    direct_api_need = next(need for need in plan.evidence_needs if need.channel == "direct_api")
    local_need = next(need for need in plan.evidence_needs if need.channel == "local_cache")
    assert direct_api_need.source_ids == ["fred-api"]
    assert local_need.source_ids == ["fred-api"]


def test_understand_query_infers_company_ticker_and_week_window() -> None:
    context = build_context(
        user_query="What changed with Apple this week?",
        intent="general_research",
        domains=[],
        regions=[],
    )

    understanding = understand_query(context)

    assert understanding.inferred_intent == "company_research"
    assert understanding.companies == ["Apple"]
    assert understanding.tickers == ["AAPL"]
    assert understanding.time_window == "week"
    assert understanding.requires_live_web is True
    assert "Companies and Earnings" in understanding.domains


def test_understand_query_infers_market_sector_and_brief_style() -> None:
    context = build_context(
        user_query="Give me a quick update on AI and chip stocks",
        intent="general_research",
        domains=[],
        regions=[],
    )

    understanding = understand_query(context)

    assert understanding.inferred_intent == "market_research"
    assert understanding.answer_style == "brief"
    assert "technology" in understanding.topics
    assert "Technology" in understanding.sectors
    assert "Technology and AI" in understanding.domains


def test_research_workflow_plan_builds_multiple_search_queries() -> None:
    context = build_context(
        user_query="What is happening with Nvidia earnings and AI demand today?",
        intent="general_research",
        domains=[],
        regions=[],
    )

    plan = build_research_workflow_plan(context, ["CompanyAgent", "MarketAgent"])

    live_web_need = next(need for need in plan.evidence_needs if need.channel == "live_web")
    assert plan.query_understanding is not None
    assert plan.query_understanding.companies == ["Nvidia"]
    assert plan.query_understanding.tickers == ["NVDA"]
    assert len(live_web_need.search_queries) >= 3
    assert any("earnings filings investor relations latest news" in query for query in live_web_need.search_queries)
