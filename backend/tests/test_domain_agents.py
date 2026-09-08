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
from app.db.models import Article, EconomicObservation, Source, SourceHealth
from app.schemas.agent import AgentCitation, AgentContext
from app.schemas.evidence_packet import EvidencePacket, EvidencePacketItem, EvidenceRetrievalStatus
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
            SourceHealth(
                source=news_source,
                source_key="bbc-news-rss",
                status="fresh",
                last_attempt_at=now - timedelta(hours=3),
                last_success_at=now - timedelta(hours=3),
                freshness_window_hours=24,
                stale_after=now + timedelta(hours=21),
            ),
            SourceHealth(
                source=fred_source,
                source_key="fred-api",
                status="fresh",
                last_attempt_at=now - timedelta(days=1),
                last_success_at=now - timedelta(days=1),
                freshness_window_hours=24,
                stale_after=now + timedelta(hours=1),
            ),
            SourceHealth(
                source=sec_source,
                source_key="sec-edgar-rss",
                status="stale",
                last_attempt_at=now - timedelta(days=3),
                last_success_at=now - timedelta(days=3),
                freshness_window_hours=24,
                stale_after=now - timedelta(days=2),
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


def test_domain_agent_prefers_fused_live_web_packet() -> None:
    packet = EvidencePacket(
        request_id="request-1",
        query="What is happening with housing in Arizona?",
        items=[
            EvidencePacketItem(
                source_kind="live_web",
                source_id="tavily",
                source_name="Tavily Live Web",
                title="Arizona housing market update",
                url="https://www.reuters.com/markets/us/arizona-housing",
                publisher="reuters.com",
                published_at="2026-09-08",
                scope="Arizona",
                summary="Arizona housing demand and inventory shifted in the latest market update.",
                source_quality="reputable",
                relevance_score=0.94,
                rank_score=140,
                citation=AgentCitation(
                    source_id="tavily",
                    title="Arizona housing market update",
                    url="https://www.reuters.com/markets/us/arizona-housing",
                    publisher="reuters.com",
                    published_at="2026-09-08",
                    supports_claim="Live web source retrieved for Arizona housing.",
                ),
            ),
            EvidencePacketItem(
                source_kind="direct_api",
                source_id="fhfa-hpi",
                source_name="FHFA House Price Index",
                title="FHFA All-Transactions HPI - Arizona",
                publisher="FHFA House Price Index",
                published_at="2026-08-30",
                scope="Arizona",
                summary="The Arizona house price index was 456.7 for 2026Q2.",
                source_quality="primary",
                relevance_score=4,
                rank_score=120,
                citation=AgentCitation(
                    source_id="fhfa-hpi",
                    title="FHFA All-Transactions HPI - Arizona",
                    publisher="FHFA House Price Index",
                    published_at="2026-08-30",
                    supports_claim="Official state HPI evidence retrieved for Arizona.",
                ),
                metadata={"domains": "Housing and Real Estate"},
            ),
        ],
        retrieval_statuses=[
            EvidenceRetrievalStatus(
                channel="live_web",
                status="success",
                query="Arizona housing",
                message="Retrieved 1 citation-ready live web result.",
            )
        ],
    )

    with build_session() as session:
        summarizer = RecordingSummarizer()
        agent = HousingAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(
            build_context(
                user_query="What is happening with housing in Arizona?",
                domains=["Housing and Real Estate"],
                regions=["Arizona"],
                evidence_packet=packet.model_dump(),
            )
        )

    assert result.agent_name == "HousingAgent"
    assert "Fused evidence source path:" in summarizer.evidence
    assert "live_web reputable: Arizona housing market update" in summarizer.evidence
    assert "direct_api primary: FHFA All-Transactions HPI - Arizona" in summarizer.evidence
    assert result.summary == "HousingAgent summary from evidence"
    assert any(citation.source_id == "tavily" for citation in result.citations)
    assert result.confidence == "medium"


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
    assert "Source fallback summary: Source path: used local stored evidence." in summarizer.evidence
    assert result.citations


def test_domain_agent_reports_stale_source_coverage_gap() -> None:
    with build_session() as session:
        seed_domain_evidence(session)
        summarizer = RecordingSummarizer()
        agent = CompanyAgent(ResearchEvidenceRepository(session), summarizer)

        result = agent.run(build_context(tickers=["AAPL"], companies=["Apple"]))

    assert "Coverage gaps: stale: sec-edgar-rss." in summarizer.evidence
    assert any("stale: sec-edgar-rss" in risk for risk in result.risks)


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
    assert "local mortgage-rate data was not found" in summarizer.evidence


def test_domain_agent_returns_missing_data_result() -> None:
    with build_session() as session:
        agent = NewsDigestAgent(ResearchEvidenceRepository(session), TemplateResearchSummarizer())

        result = agent.run(build_context())

    assert result.confidence == "low"
    assert result.citations == []
    assert "did not find enough current ingested evidence" in result.summary
    assert "checked local stored evidence but found no matching records" in result.summary
    assert result.claims[0].claim_type == "fact"


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
