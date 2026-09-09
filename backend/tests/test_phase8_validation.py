from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.model_client import TemplateResearchSummarizer
from app.db.base import Base
from app.db.models import Article, EconomicObservation, Source, UserSettings
from app.schemas.agent import AgentQueryRequest
from app.schemas.live_web import LiveWebCitation, LiveWebEvidence, LiveWebSearchResponse
from app.services import agents, evidence_fusion


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_phase8_sources(session):
    now = datetime.now(UTC)
    fhfa = Source(
        name="FHFA House Price Index",
        base_url="https://www.fhfa.gov",
        source_type="official_dataset",
        domains=["Housing and Real Estate"],
        access_method="download",
    )
    fred = Source(
        name="FRED API",
        base_url="https://fred.stlouisfed.org",
        source_type="official_api",
        domains=["U.S. Economy and Policy", "Markets and Rates"],
        access_method="api",
    )
    sec = Source(
        name="SEC EDGAR RSS",
        base_url="https://www.sec.gov",
        source_type="official_rss",
        domains=["Companies and Earnings", "Regulation and Legal"],
        access_method="rss",
    )
    session.add_all([fhfa, fred, sec])
    session.flush()
    session.add_all(
        [
            EconomicObservation(
                source=fhfa,
                series_id="FHFA_HPI:STATE:AZ",
                series_name="FHFA All-Transactions HPI - Arizona",
                value=456.7,
                unit="index",
                period="2026Q2",
                released_at=now - timedelta(days=20),
                retrieved_at=now - timedelta(days=1),
                region="Arizona",
            ),
            EconomicObservation(
                source=fred,
                series_id="MORTGAGE30US",
                series_name="30-Year Fixed Rate Mortgage Average",
                value=6.71,
                unit="percent",
                period="2026-09-03",
                released_at=now - timedelta(days=5),
                retrieved_at=now - timedelta(days=1),
                region="United States",
            ),
            Article(
                source=sec,
                title="Apple files quarterly update",
                url="https://www.sec.gov/example/aapl",
                publisher="SEC",
                published_at=now - timedelta(days=3),
                retrieved_at=now - timedelta(days=3),
                summary="Apple filed a recent company update.",
                domains=["Companies and Earnings"],
                tickers=["AAPL"],
                companies=["Apple"],
                regions=["United States"],
            ),
            UserSettings(
                watchlist_tickers=["AAPL", "MSFT"],
                preferred_regions=["Arizona"],
                enabled_sources=["newsapi", "fred-api"],
                daily_briefing_time="08:00",
                daily_schedule_enabled=False,
                daily_schedule_timezone="local",
                daily_schedule_mode="all",
                daily_report_enabled=False,
            ),
        ]
    )
    session.commit()


def fake_live_web_search(request):
    query = request.query.lower()
    if "watchlist" in query or ("aapl" in query and "msft" in query):
        return build_live_response(
            request.query,
            "Watchlist market update",
            "AAPL and MSFT were part of the latest market watchlist scan.",
            "https://www.reuters.com/markets/watchlist-example",
            "reuters.com",
        )
    if "mortgage" in query:
        return build_live_response(
            request.query,
            "Mortgage rates remain a national affordability pressure",
            "Freddie Mac reported national mortgage-rate context; Arizona-specific mortgage-rate evidence is not always directly available.",
            "https://www.freddiemac.com/pmms",
            "freddiemac.com",
            quality="provider",
        )
    if "apple" in query or "aapl" in query:
        return build_live_response(
            request.query,
            "Apple latest company news",
            "Apple-related news this week focused on company updates, product demand, and market reaction.",
            "https://www.reuters.com/technology/apple-example",
            "reuters.com",
        )
    if "housing" in query or "arizona" in query:
        return build_live_response(
            request.query,
            "Arizona housing market update",
            "Arizona housing conditions are being shaped by affordability, inventory, and mortgage-rate pressure.",
            "https://www.reuters.com/markets/us/arizona-housing",
            "reuters.com",
        )
    return build_live_response(
        request.query,
        "Current broad market update",
        "Live web evidence supplied a current answer even without matching local stored records.",
        "https://www.reuters.com/markets/current-example",
        "reuters.com",
    )


def build_live_response(
    query: str,
    title: str,
    excerpt: str,
    url: str,
    publisher: str,
    *,
    quality: str = "reputable",
) -> LiveWebSearchResponse:
    return LiveWebSearchResponse(
        provider="tavily",
        status="success",
        query=query,
        message="Retrieved 1 citation-ready live web result.",
        results=[
            LiveWebEvidence(
                title=title,
                url=url,
                publisher=publisher,
                published_at="2026-09-08",
                retrieved_at="2026-09-08T12:00:00+00:00",
                excerpt=excerpt,
                source_quality=quality,
                relevance_score=0.9,
                citation=LiveWebCitation(
                    title=title,
                    url=url,
                    publisher=publisher,
                    published_at="2026-09-08",
                    retrieved_at="2026-09-08T12:00:00+00:00",
                    supports_claim=f"Live web source retrieved for {query}.",
                    source_quality=quality,
                ),
            )
        ],
    )


@pytest.mark.parametrize(
    ("question", "expected_text", "expected_agents"),
    [
        ("What is happening with housing in Arizona?", "Arizona housing conditions", {"HousingAgent"}),
        ("What are mortgage rates in AZ?", "national mortgage-rate context", {"HousingAgent", "MarketAgent"}),
        ("What matters for my watchlist today?", "AAPL and MSFT", {"CompanyAgent", "MarketAgent"}),
        ("What changed with Apple this week?", "Apple-related news this week", {"CompanyAgent"}),
        (
            "Tell me what is happening in markets right now even if my local data is thin",
            "current answer even without matching local stored records",
            {"MarketAgent"},
        ),
    ],
)
def test_phase8_regression_questions_use_web_first_clean_answer(
    monkeypatch,
    question: str,
    expected_text: str,
    expected_agents: set[str],
) -> None:
    monkeypatch.setattr(evidence_fusion, "run_live_web_search", fake_live_web_search)
    monkeypatch.setattr(agents, "build_default_summarizer", lambda: TemplateResearchSummarizer())

    session_factory = build_session_factory()
    with session_factory() as session:
        seed_phase8_sources(session)

        response = agents.run_agent_query(AgentQueryRequest(user_query=question), session)

    assert expected_text in response.summary
    assert "Coordinator selected" not in response.summary
    assert "Source path:" not in response.summary
    assert "Fused evidence source path" not in response.summary
    assert "Sources:" not in response.summary
    assert "Major Trends:" in response.summary
    assert any(citation.source_id == "tavily" for citation in response.citations)
    assert "EvidenceFusionAgent" in response.agents_ran
    assert expected_agents.issubset(set(response.agents_ran))
    assert response.guardrail.status == "passed"


def test_phase8_live_web_failure_still_uses_supporting_api_evidence(monkeypatch) -> None:
    def skipped_live_web(request):
        return LiveWebSearchResponse(
            provider="tavily",
            status="skipped",
            query=request.query,
            message="Missing required API key setting: TAVILY_API_KEY",
        )

    monkeypatch.setattr(evidence_fusion, "run_live_web_search", skipped_live_web)
    monkeypatch.setattr(agents, "build_default_summarizer", lambda: TemplateResearchSummarizer())

    session_factory = build_session_factory()
    with session_factory() as session:
        seed_phase8_sources(session)

        response = agents.run_agent_query(
            AgentQueryRequest(user_query="What are mortgage rates in AZ?"),
            session,
        )

    assert "30-Year Fixed Mortgage Rate" in response.summary
    assert any(citation.source_id == "fred-api" for citation in response.citations)
    assert response.requires_guardrail_review is False
