from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.domain_agents import (
    CompanyAgent,
    HousingAgent,
    MacroAgent,
    MarketAgent,
    NewsDigestAgent,
    build_domain_agents,
)
from app.agents.model_client import TemplateResearchSummarizer, extract_response_text, output_item_types
from app.db.base import Base
from app.db.models import Article, EconomicObservation, Source
from app.schemas.agent import AgentContext
from app.services.research_evidence import ResearchEvidenceRepository


class RecordingSummarizer:
    def __init__(self) -> None:
        self.evidence = ""
        self.agent_name = ""

    def summarize(self, *, agent_name: str, instructions: str, evidence: str) -> str:
        self.agent_name = agent_name
        self.evidence = evidence
        return f"{agent_name} summary from evidence"


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def seed_domain_evidence(session):
    now = datetime.now(UTC)
    news_source = Source(
        name="BBC News RSS",
        base_url="https://www.bbc.com/news",
        source_type="official_rss",
        domains=["World and Geopolitics", "Markets and Rates"],
        access_method="rss",
    )
    sec_source = Source(
        name="SEC EDGAR RSS",
        base_url="https://www.sec.gov",
        source_type="official_rss",
        domains=["Companies and Earnings", "Regulation and Legal"],
        access_method="rss",
    )
    fred_source = Source(
        name="FRED API",
        base_url="https://fred.stlouisfed.org",
        source_type="official_api",
        domains=["U.S. Economy and Policy", "Markets and Rates"],
        access_method="api",
    )
    session.add_all([news_source, sec_source, fred_source])
    session.flush()

    session.add_all(
        [
            Article(
                source=news_source,
                title="Global markets react to policy news",
                url="https://example.com/global-markets",
                publisher="BBC",
                published_at=now - timedelta(hours=4),
                retrieved_at=now - timedelta(hours=3),
                summary="Markets reacted to new policy signals.",
                domains=["World and Geopolitics", "Markets and Rates"],
                regions=["US"],
            ),
            Article(
                source=sec_source,
                title="AAPL files annual report",
                url="https://example.com/aapl-10k",
                publisher="SEC",
                published_at=now - timedelta(days=2),
                retrieved_at=now - timedelta(days=2),
                summary="AAPL filed a new annual report.",
                domains=["Companies and Earnings"],
                tickers=["AAPL"],
                companies=["Apple"],
            ),
            Article(
                source=news_source,
                title="Housing affordability remains pressured",
                url="https://example.com/housing",
                publisher="BBC",
                published_at=now - timedelta(days=3),
                retrieved_at=now - timedelta(days=3),
                summary="Mortgage rates kept affordability in focus.",
                domains=["Housing and Real Estate"],
                regions=["US"],
            ),
            EconomicObservation(
                source=fred_source,
                series_id="FEDFUNDS",
                series_name="FEDFUNDS",
                value=4.5,
                unit="percent",
                period="2026-08-01",
                released_at=now - timedelta(days=10),
                retrieved_at=now - timedelta(days=9),
                region="US",
            ),
            EconomicObservation(
                source=fred_source,
                series_id="UNRATE",
                series_name="UNRATE",
                value=4.3,
                unit="percent",
                period="2026-08-01",
                released_at=now - timedelta(days=8),
                retrieved_at=now - timedelta(days=7),
                region="US",
            ),
            EconomicObservation(
                source=fred_source,
                series_id="MORTGAGE30US",
                series_name="MORTGAGE30US",
                value=6.8,
                unit="percent",
                period="2026-08-27",
                released_at=now - timedelta(days=6),
                retrieved_at=now - timedelta(days=5),
                region="US",
            ),
        ]
    )
    session.commit()


def build_context(**overrides) -> AgentContext:
    values = {
        "request_id": "request-1",
        "user_query": "What should I watch?",
        "intent": "general_research",
        "domains": [],
        "tickers": [],
        "companies": [],
        "regions": [],
        "time_window": "month",
        "source_ids": [],
        "safety_level": "investment_research",
    }
    values.update(overrides)
    return AgentContext(**values)


def test_news_digest_agent_produces_cited_result() -> None:
    with build_session() as session:
        seed_domain_evidence(session)
        summarizer = RecordingSummarizer()
        agent = NewsDigestAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(build_context())

    assert result.agent_name == "NewsDigestAgent"
    assert result.summary == "NewsDigestAgent summary from evidence"
    assert result.citations
    assert "Global markets react" in summarizer.evidence
    assert result.confidence in {"low", "medium", "high"}


def test_company_agent_filters_by_ticker() -> None:
    with build_session() as session:
        seed_domain_evidence(session)
        summarizer = RecordingSummarizer()
        agent = CompanyAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(build_context(tickers=["AAPL"], companies=["Apple"]))

    assert result.agent_name == "CompanyAgent"
    assert "AAPL files annual report" in summarizer.evidence
    assert all(citation.source_id == "sec-edgar-rss" for citation in result.citations)


def test_market_agent_uses_market_observations() -> None:
    with build_session() as session:
        seed_domain_evidence(session)
        summarizer = RecordingSummarizer()
        agent = MarketAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(build_context(domains=["Markets and Rates"], regions=["US"]))

    assert result.agent_name == "MarketAgent"
    assert "Federal Funds Rate (FEDFUNDS)" in summarizer.evidence
    assert "Unemployment Rate (UNRATE)" in summarizer.evidence
    assert result.citations


def test_macro_agent_uses_macro_series() -> None:
    with build_session() as session:
        seed_domain_evidence(session)
        summarizer = RecordingSummarizer()
        agent = MacroAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(build_context(regions=["US"]))

    assert result.agent_name == "MacroAgent"
    assert "Federal Funds Rate (FEDFUNDS)" in summarizer.evidence
    assert "Unemployment Rate (UNRATE)" in summarizer.evidence


def test_housing_agent_uses_housing_article_and_mortgage_series() -> None:
    with build_session() as session:
        seed_domain_evidence(session)
        summarizer = RecordingSummarizer()
        agent = HousingAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(build_context(domains=["Housing and Real Estate"], regions=["US"]))

    assert result.agent_name == "HousingAgent"
    assert "Housing affordability" in summarizer.evidence
    assert "30-Year Fixed Mortgage Rate (MORTGAGE30US)" in summarizer.evidence


def test_housing_agent_uses_regional_fhfa_and_national_mortgage_context() -> None:
    now = datetime.now(UTC)

    with build_session() as session:
        seed_domain_evidence(session)
        fred_source = session.query(Source).filter(Source.name == "FRED API").one()
        session.add_all(
            [
                EconomicObservation(
                    source=fred_source,
                    series_id="FHFA_HPI:METRO:38060",
                    series_name="FHFA All-Transactions HPI - Phoenix-Mesa-Chandler, AZ",
                    value=350.44,
                    unit="index",
                    period="2026Q2",
                    released_at=now - timedelta(days=150),
                    retrieved_at=now - timedelta(days=1),
                    region="Phoenix-Mesa-Chandler, AZ",
                ),
                EconomicObservation(
                    source=fred_source,
                    series_id="FREDDIE_PMMS:30Y_FIXED",
                    series_name="Freddie Mac PMMS - 30-Year Fixed-Rate Mortgage",
                    value=6.71,
                    unit="percent",
                    period="2026-09-03",
                    released_at=now - timedelta(days=2),
                    retrieved_at=now - timedelta(days=1),
                    region="United States",
                ),
            ]
        )
        session.commit()
        summarizer = RecordingSummarizer()
        agent = HousingAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(
            build_context(
                user_query="Is Phoenix housing cooling?",
                domains=["Housing and Real Estate"],
                regions=["Phoenix"],
            )
        )

    assert result.agent_name == "HousingAgent"
    assert "Phoenix-Mesa-Chandler, AZ" in summarizer.evidence
    assert "Freddie Mac PMMS - 30-Year Fixed-Rate Mortgage" in summarizer.evidence
    assert "for United States" in summarizer.evidence


def test_domain_agent_returns_missing_data_result() -> None:
    with build_session() as session:
        agent = NewsDigestAgent(ResearchEvidenceRepository(session), TemplateResearchSummarizer())

        result = agent.run(build_context())

    assert result.confidence == "low"
    assert result.citations == []
    assert "did not find enough current ingested evidence" in result.summary


def test_build_domain_agents_returns_all_specialists() -> None:
    with build_session() as session:
        agents = build_domain_agents(ResearchEvidenceRepository(session), TemplateResearchSummarizer())

    assert [agent.name for agent in agents] == [
        "NewsDigestAgent",
        "CompanyAgent",
        "MarketAgent",
        "MacroAgent",
        "HousingAgent",
    ]


def test_extract_response_text_handles_responses_api_output_text() -> None:
    assert extract_response_text({"output_text": "  model summary  "}) == "model summary"


def test_extract_response_text_handles_nested_output_content() -> None:
    body = {"output": [{"content": [{"text": "first"}, {"text": "second"}]}]}

    assert extract_response_text(body) == "first\nsecond"


def test_output_item_types_summarizes_raw_response_shape() -> None:
    body = {"output": [{"type": "reasoning"}, {"type": "message"}, {"content": []}, "ignored"]}

    assert output_item_types(body) == ["reasoning", "message", "unknown"]
