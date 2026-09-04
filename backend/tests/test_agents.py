from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.agents.model_client import TemplateResearchSummarizer
from app.db.base import Base
from app.db.models import AgentRun
from app.schemas.agent import AgentCitation, AgentContext, AgentQueryRequest, AgentResult
from app.services import agents
from app.services.citations import format_citation, format_sources_section
from app.services.guardrails import (
    FINANCIAL_DISCLAIMER,
    check_investment_guardrails,
    enforce_agent_guardrails,
    find_banned_direct_advice_phrases,
)


client = TestClient(app)


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def test_agent_query_endpoint_runs_coordinator_and_domain_agents(monkeypatch) -> None:
    monkeypatch.setattr(agents, "build_default_summarizer", lambda: TemplateResearchSummarizer())

    response = client.post(
        "/api/v1/agents/query",
        json={
            "user_query": "What should I watch in markets today?",
            "intent": "market_research",
            "domains": ["Markets and Rates"],
            "tickers": ["SPY"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["agents_ran"] == [
        "CoordinatorAgent",
        "CompanyAgent",
        "MarketAgent",
        "MacroAgent",
        "CitationAgent",
        "RiskGuardrailAgent",
    ]
    assert payload["guardrail"]["status"] == "passed"
    assert payload["requires_guardrail_review"] is False
    assert "not financial advice" in payload["summary"].lower()
    assert "not a recommendation" in payload["summary"].lower()
    assert "coordinator selected" in payload["summary"].lower()


def test_agent_query_endpoint_rejects_empty_query() -> None:
    response = client.post("/api/v1/agents/query", json={"user_query": ""})

    assert response.status_code == 422


def test_agent_runs_endpoint_returns_history() -> None:
    response = client.get("/api/v1/agents/runs?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert "runs" in payload
    assert "total" in payload


def test_guardrail_detects_direct_advice_phrases() -> None:
    text = f"{FINANCIAL_DISCLAIMER} You should buy this stock."

    result = check_investment_guardrails(text)

    assert result.status == "needs_revision"
    assert "you should buy" in result.banned_phrases_found


def test_guardrail_detects_missing_disclaimer() -> None:
    result = check_investment_guardrails("A bullish scenario may depend on rates falling.")

    assert result.status == "needs_revision"
    assert "Output is missing the required financial disclaimer." in result.issues


def test_banned_phrase_detection_is_case_insensitive() -> None:
    phrases = find_banned_direct_advice_phrases("This is a GUARANTEED RETURN.")

    assert phrases == ["guaranteed return"]


def test_route_agent_names_for_housing_macro_query() -> None:
    context = AgentContext(
        request_id="request-1",
        user_query="How do mortgage rates affect housing?",
        intent="housing_macro_research",
        regions=["US"],
    )

    assert agents.route_agent_names(context) == ["MarketAgent", "MacroAgent", "HousingAgent"]


def test_route_agent_names_for_general_update_defaults_to_news_and_market() -> None:
    context = AgentContext(
        request_id="request-2",
        user_query="Give me a quick update",
        intent="general_research",
    )

    assert agents.route_agent_names(context) == ["NewsDigestAgent", "MarketAgent"]


def test_synthesis_preserves_specialist_outputs_and_risks() -> None:
    request = AgentQueryRequest(user_query="What matters for markets?")

    result = agents.synthesize_agent_results(
        [
            AgentResult(agent_name="CoordinatorAgent", summary="Coordinator selected: MarketAgent."),
            AgentResult(
                agent_name="MarketAgent",
                summary="Rates are central to the setup.",
                confidence="medium",
                risks=["Evidence is limited."],
            ),
        ],
        request=request,
    )

    assert "not financial advice" in result.lower()
    assert "Coordinator selected: MarketAgent." in result
    assert "SynthesisAgent reviewed the available evidence" in result
    assert "MarketAgent (medium confidence): Rates are central to the setup." in result
    assert "Evidence is limited." in result


def test_format_synthesis_evidence_includes_user_query_and_citations() -> None:
    evidence = agents.format_synthesis_evidence(
        [
            AgentResult(
                agent_name="MarketAgent",
                summary="Rates are central to the setup.",
                confidence="medium",
            )
        ],
        [
            AgentCitation(
                source_id="fred-api",
                title="Federal Funds Rate",
                publisher="FRED",
                retrieved_at="2026-09-04T12:00:00+00:00",
                supports_claim="Economic observation evidence retrieved for the agent query.",
            )
        ],
        AgentQueryRequest(
            user_query="What should I watch?",
            intent="market_research",
            domains=["Markets and Rates"],
            tickers=["SPY"],
        ),
    )

    assert "User question: What should I watch?" in evidence
    assert "Requested domains: Markets and Rates" in evidence
    assert "Requested tickers: SPY" in evidence
    assert "Federal Funds Rate" in evidence


def test_citation_format_includes_source_dates_and_url() -> None:
    citation = AgentCitation(
        source_id="bbc-news-rss",
        title="Markets react",
        url="https://example.com/markets",
        publisher="BBC",
        published_at="2026-09-04T12:00:00+00:00",
        retrieved_at="2026-09-04T13:00:00+00:00",
        supports_claim="Markets reacted to rate expectations.",
    )

    formatted = format_citation(citation)

    assert "Markets react" in formatted
    assert "BBC" in formatted
    assert "published 2026-09-04T12:00:00+00:00" in formatted
    assert "retrieved 2026-09-04T13:00:00+00:00" in formatted
    assert "https://example.com/markets" in formatted


def test_sources_section_handles_missing_citations() -> None:
    assert format_sources_section([]) == "Sources:\n- No source citations were available for this response."


def test_agent_guardrail_blocks_direct_investment_advice() -> None:
    check = enforce_agent_guardrails(
        f"{FINANCIAL_DISCLAIMER} You should buy this stock.",
        request=AgentQueryRequest(user_query="Should I buy SPY?"),
        citations=[
            AgentCitation(
                source_id="bbc-news-rss",
                title="Markets react",
                supports_claim="Markets moved.",
            )
        ],
        confidence="medium",
    )

    assert check.status == "blocked"
    assert "you should buy" in check.banned_phrases_found
    assert check.rewritten_text is not None
    assert "you should buy" not in check.rewritten_text.lower()


def test_agent_guardrail_flags_low_confidence_without_citations() -> None:
    check = enforce_agent_guardrails(
        f"{FINANCIAL_DISCLAIMER} I do not have enough current source-backed evidence.",
        request=AgentQueryRequest(user_query="What happens to stocks?", safety_level="investment_research"),
        citations=[],
        confidence="low",
    )

    assert check.status == "needs_revision"
    assert "Investment-oriented response has no citations." in check.issues
    assert "Response confidence is low; answer must clearly state uncertainty." in check.issues


def test_agent_guardrail_flags_unsupported_price_targets() -> None:
    check = enforce_agent_guardrails(
        f"{FINANCIAL_DISCLAIMER} A price target could move to $500.",
        request=AgentQueryRequest(user_query="What is the target?"),
        citations=[
            AgentCitation(
                source_id="sec-edgar-rss",
                title="Company filing",
                supports_claim="Company filed annual report.",
            )
        ],
        confidence="medium",
    )

    assert check.status == "needs_revision"
    assert "Output contains an unsupported price-target style statement." in check.issues


def test_build_agent_response_uses_rewritten_safe_summary() -> None:
    response = agents.build_agent_response(
        "request-1",
        [
            AgentResult(
                agent_name="MarketAgent",
                summary=f"{FINANCIAL_DISCLAIMER} You should sell this stock.",
                confidence="medium",
                citations=[
                    AgentCitation(
                        source_id="bbc-news-rss",
                        title="Markets react",
                        supports_claim="Markets moved.",
                    )
                ],
            )
        ],
        AgentQueryRequest(user_query="Should I sell?"),
    )

    assert response.guardrail.status == "blocked"
    assert "you should sell" not in response.summary.lower()
    assert response.requires_guardrail_review is True


def test_list_agent_runs_orders_latest_first() -> None:
    with build_session() as session:
        session.add_all(
            [
                AgentRun(
                    request_id="request-old",
                    agent_name="MarketAgent",
                    status="success",
                    started_at=None,
                ),
                AgentRun(
                    request_id="request-new",
                    agent_name="MacroAgent",
                    status="failed",
                    error="failed",
                ),
            ]
        )
        session.commit()

        history = agents.list_agent_runs(session, limit=10)

    assert history.total == 2
    assert [run.request_id for run in history.runs] == ["request-new", "request-old"]
    assert history.runs[0].agent_name == "MacroAgent"
    assert history.runs[0].status == "failed"
