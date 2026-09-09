from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Article, EconomicObservation, Report, Source
from app.schemas.agent import AgentContext
from app.schemas.live_web import LiveWebCitation, LiveWebEvidence, LiveWebSearchResponse
from app.services import evidence_fusion
from app.services.evidence_fusion import build_evidence_packet
from app.services.research_workflow import build_research_workflow_plan


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def seed_packet_evidence(session):
    now = datetime.now(UTC)
    bbc = Source(
        name="BBC News RSS",
        base_url="https://www.bbc.com/news",
        source_type="official_rss",
        domains=["Housing and Real Estate"],
        access_method="rss",
    )
    fhfa = Source(
        name="FHFA House Price Index",
        base_url="https://www.fhfa.gov",
        source_type="official_dataset",
        domains=["Housing and Real Estate"],
        access_method="download",
    )
    session.add_all([bbc, fhfa])
    session.flush()
    session.add_all(
        [
            Article(
                source=bbc,
                title="Arizona housing inventory watch",
                url="https://example.com/arizona-housing",
                publisher="BBC",
                published_at=now - timedelta(hours=3),
                retrieved_at=now - timedelta(hours=2),
                summary="Arizona housing inventory is an important regional signal.",
                excerpt="Inventory changed.",
                domains=["Housing and Real Estate"],
                tickers=[],
                companies=[],
                regions=["Arizona"],
            ),
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
            Report(
                report_type="housing_macro",
                status="published",
                title="Saved Arizona Housing Brief",
                summary="Previous saved report mentioned Arizona affordability pressure.",
                body="Previous saved report mentioned Arizona affordability pressure.",
                domains=["Housing and Real Estate"],
                tickers=[],
                companies=[],
                as_of=now - timedelta(days=2),
                confidence="medium",
                guardrail_status="passed",
            ),
        ]
    )
    session.commit()


def fake_live_web_response(query: str) -> LiveWebSearchResponse:
    return LiveWebSearchResponse(
        provider="tavily",
        status="success",
        query=query,
        message="Retrieved 1 citation-ready live web results.",
        results=[
            LiveWebEvidence(
                title="Arizona housing market update",
                url="https://www.reuters.com/markets/us/arizona-housing",
                publisher="reuters.com",
                published_at="2026-09-08",
                retrieved_at="2026-09-08T12:00:00+00:00",
                excerpt="Arizona housing demand and supply conditions changed in the latest market update.",
                source_quality="reputable",
                relevance_score=0.92,
                citation=LiveWebCitation(
                    title="Arizona housing market update",
                    url="https://www.reuters.com/markets/us/arizona-housing",
                    publisher="reuters.com",
                    published_at="2026-09-08",
                    retrieved_at="2026-09-08T12:00:00+00:00",
                    supports_claim="Live web reputable source result retrieved for Arizona housing.",
                    source_quality="reputable",
                ),
            )
        ],
    )


def test_evidence_packet_fuses_live_web_api_local_and_reports(monkeypatch) -> None:
    def fake_run_live_web_search(request):
        return fake_live_web_response(request.query)

    monkeypatch.setattr(evidence_fusion, "run_live_web_search", fake_run_live_web_search)

    with build_session() as session:
        seed_packet_evidence(session)
        context = AgentContext(
            request_id="request-1",
            user_query="What is happening with housing in Arizona?",
            intent="general_research",
        )
        plan = build_research_workflow_plan(context, ["HousingAgent"])

        packet = build_evidence_packet(context=context, plan=plan, session=session)

    assert packet.items[0].source_kind == "live_web"
    assert any(item.source_kind == "direct_api" and item.source_id == "fhfa-hpi" for item in packet.items)
    assert any(item.source_kind == "local_cache" and item.source_id == "bbc-news-rss" for item in packet.items)
    assert any(item.source_kind == "saved_report" for item in packet.items)
    assert any(citation.source_id == "tavily" for citation in packet.citations)
    assert {status.channel for status in packet.retrieval_statuses} == {"live_web", "direct_api", "local_cache"}


def test_evidence_packet_records_live_web_skipped_status(monkeypatch) -> None:
    def fake_run_live_web_search(request):
        return LiveWebSearchResponse(
            provider="tavily",
            status="skipped",
            query=request.query,
            message="Missing required API key setting: TAVILY_API_KEY",
        )

    monkeypatch.setattr(evidence_fusion, "run_live_web_search", fake_run_live_web_search)

    with build_session() as session:
        seed_packet_evidence(session)
        context = AgentContext(
            request_id="request-2",
            user_query="What is happening with housing in Arizona?",
            intent="general_research",
        )
        plan = build_research_workflow_plan(context, ["HousingAgent"])

        packet = build_evidence_packet(context=context, plan=plan, session=session)

    assert any(
        status.channel == "live_web"
        and status.status == "skipped"
        and "TAVILY_API_KEY" in status.message
        for status in packet.retrieval_statuses
    )
    assert any(item.source_kind == "direct_api" for item in packet.items)


def test_evidence_packet_uses_one_shared_live_web_search(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run_live_web_search(request):
        calls.append(request.query)
        return fake_live_web_response(request.query)

    monkeypatch.setattr(evidence_fusion, "run_live_web_search", fake_run_live_web_search)

    with build_session() as session:
        seed_packet_evidence(session)
        context = AgentContext(
            request_id="request-3",
            user_query="What is happening with housing in Arizona and mortgage rates this week?",
            intent="general_research",
        )
        plan = build_research_workflow_plan(context, ["HousingAgent", "MacroAgent"])

        packet = build_evidence_packet(context=context, plan=plan, session=session)

    assert len(calls) == 1
    assert packet.retrieval_statuses[0].channel == "live_web"
    assert any(item.source_kind == "live_web" for item in packet.items)
