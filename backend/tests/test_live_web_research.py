from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.schemas.live_web import LiveWebSearchRequest
from app.services import live_web_research
from app.services.live_web_research import (
    classify_source_quality,
    run_live_web_search,
    tavily_payload_to_evidence,
)


client = TestClient(app)


TAVILY_SAMPLE = {
    "results": [
        {
            "title": "Arizona housing update",
            "url": "https://www.census.gov/housing/example",
            "content": "Arizona housing inventory and sales changed in the latest release.",
            "score": 0.82,
            "published_date": "2026-09-08",
        },
        {
            "title": "Social chatter",
            "url": "https://reddit.com/r/realestate/example",
            "content": "Unsourced discussion.",
            "score": 0.99,
        },
        {
            "title": "Regional market report",
            "url": "https://www.reuters.com/markets/us/example",
            "content": "Mortgage rates and inventory are shaping regional housing demand.",
            "score": 0.75,
        },
    ]
}


def test_run_live_web_search_skips_without_tavily_key() -> None:
    response = run_live_web_search(
        LiveWebSearchRequest(query="What is happening with Arizona housing?"),
        settings=Settings(tavily_api_key=None),
    )

    assert response.status == "skipped"
    assert response.message == "Missing required API key setting: TAVILY_API_KEY"
    assert response.results == []


def test_run_live_web_search_uses_tavily_adapter(monkeypatch) -> None:
    def fake_fetch_tavily_search(request: LiveWebSearchRequest, settings: Settings):
        assert request.query == "What is happening with Arizona housing?"
        assert settings.tavily_api_key == "test-key"
        return TAVILY_SAMPLE

    monkeypatch.setattr(live_web_research, "fetch_tavily_search", fake_fetch_tavily_search)

    response = run_live_web_search(
        LiveWebSearchRequest(query="What is happening with Arizona housing?"),
        settings=Settings(tavily_api_key="test-key"),
    )

    assert response.status == "success"
    assert len(response.results) == 2
    assert response.results[0].source_quality == "primary"
    assert response.results[0].citation.url == "https://www.census.gov/housing/example"
    assert all("reddit.com" not in result.url for result in response.results)


def test_tavily_payload_to_evidence_respects_include_domains() -> None:
    evidence = tavily_payload_to_evidence(
        TAVILY_SAMPLE,
        LiveWebSearchRequest(
            query="Arizona housing",
            include_domains=["reuters.com"],
        ),
    )

    assert len(evidence) == 1
    assert evidence[0].publisher == "reuters.com"
    assert evidence[0].source_quality == "reputable"


def test_classify_source_quality() -> None:
    assert classify_source_quality("https://www.fhfa.gov/data/hpi") == "primary"
    assert classify_source_quality("https://www.reuters.com/markets") == "reputable"
    assert classify_source_quality("https://www.finnhub.io/news") == "provider"
    assert classify_source_quality("https://example.com/markets") == "discovery"


def test_live_web_search_endpoint_returns_missing_key_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.agents.run_live_web_search",
        lambda request: run_live_web_search(request, settings=Settings(tavily_api_key=None)),
    )

    response = client.post("/api/v1/agents/live-web/search", json={"query": "Arizona housing"})

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    assert response.json()["message"] == "Missing required API key setting: TAVILY_API_KEY"
