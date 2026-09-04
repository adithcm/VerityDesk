from fastapi.testclient import TestClient

from app.main import app
from app.agents.model_client import TemplateResearchSummarizer
from app.schemas.agent import AgentContext, AgentResult
from app.services import agents
from app.services.guardrails import (
    FINANCIAL_DISCLAIMER,
    check_investment_guardrails,
    find_banned_direct_advice_phrases,
)


client = TestClient(app)


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
    result = agents.synthesize_agent_results(
        [
            AgentResult(agent_name="CoordinatorAgent", summary="Coordinator selected: MarketAgent."),
            AgentResult(
                agent_name="MarketAgent",
                summary="Rates are central to the setup.",
                confidence="medium",
                risks=["Evidence is limited."],
            ),
        ]
    )

    assert "not financial advice" in result.lower()
    assert "Coordinator selected: MarketAgent." in result
    assert "MarketAgent: Rates are central to the setup." in result
    assert "Evidence is limited." in result
