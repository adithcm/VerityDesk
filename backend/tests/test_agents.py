from fastapi.testclient import TestClient

from app.main import app
from app.services.guardrails import (
    FINANCIAL_DISCLAIMER,
    check_investment_guardrails,
    find_banned_direct_advice_phrases,
)


client = TestClient(app)


def test_agent_query_endpoint_returns_placeholder_contract() -> None:
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
    assert payload["agents_ran"] == ["CoordinatorAgent", "CitationAgent", "RiskGuardrailAgent"]
    assert payload["guardrail"]["status"] == "passed"
    assert payload["requires_guardrail_review"] is False
    assert "not financial advice" in payload["summary"].lower()
    assert "not a recommendation" in payload["summary"].lower()


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
