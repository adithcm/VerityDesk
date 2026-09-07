from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Article, EconomicObservation, IngestionRun, Source, SourceHealth
from app.services.research_evidence import EvidenceQuery, ResearchEvidenceRepository


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def seed_evidence(session):
    now = datetime.now(UTC)
    bbc = Source(
        name="BBC News RSS",
        base_url="https://www.bbc.com/news",
        source_type="official_rss",
        domains=["World and Geopolitics", "Markets and Rates"],
        access_method="rss",
    )
    fred = Source(
        name="FRED API",
        base_url="https://fred.stlouisfed.org",
        source_type="official_api",
        domains=["U.S. Economy and Policy", "Markets and Rates"],
        access_method="api",
    )
    session.add_all([bbc, fred])
    session.flush()

    matching_article = Article(
        source=bbc,
        title="Markets watch rate expectations",
        url="https://example.com/markets-rates",
        publisher="BBC",
        published_at=now - timedelta(hours=2),
        retrieved_at=now - timedelta(hours=1),
        summary="Markets moved as rate expectations changed.",
        excerpt="Rate expectations changed.",
        domains=["Markets and Rates"],
        tickers=["SPY"],
        companies=[],
        regions=["US"],
    )
    older_article = Article(
        source=bbc,
        title="Older world update",
        url="https://example.com/older-world",
        publisher="BBC",
        published_at=now - timedelta(days=45),
        retrieved_at=now - timedelta(days=45),
        domains=["World and Geopolitics"],
        tickers=[],
        companies=[],
        regions=[],
    )
    observation = EconomicObservation(
        source=fred,
        series_id="UNRATE",
        series_name="UNRATE",
        value=4.3,
        unit="percent",
        period="2026-08-01",
        released_at=now - timedelta(days=3),
        retrieved_at=now - timedelta(days=1),
        region="US",
    )
    health = SourceHealth(
        source=bbc,
        source_key="bbc-news-rss",
        status="fresh",
        last_attempt_at=now - timedelta(hours=1),
        last_success_at=now - timedelta(hours=1),
        latest_item_title=matching_article.title,
        freshness_window_hours=24,
        stale_after=now + timedelta(hours=23),
    )
    run = IngestionRun(
        source=bbc,
        source_key="bbc-news-rss",
        run_type="manual",
        status="success",
        started_at=now - timedelta(hours=1),
        completed_at=now - timedelta(minutes=55),
        items_seen=3,
        items_inserted=1,
        items_updated=2,
        items_skipped=0,
    )
    session.add_all([matching_article, older_article, observation, health, run])
    session.commit()


def test_latest_articles_filters_by_domain_ticker_and_time_window() -> None:
    with build_session() as session:
        seed_evidence(session)
        repository = ResearchEvidenceRepository(session)

        results = repository.latest_articles(
            EvidenceQuery(domains=["Markets and Rates"], tickers=["SPY"], time_window="week", limit=5)
        )

    assert len(results) == 1
    assert results[0].title == "Markets watch rate expectations"
    assert results[0].source_id == "bbc-news-rss"
    assert results[0].citation.title == "Markets watch rate expectations"
    assert results[0].citation.url == "https://example.com/markets-rates"
    assert results[0].relevance_score > 0


def test_latest_articles_excludes_outside_time_window() -> None:
    with build_session() as session:
        seed_evidence(session)
        repository = ResearchEvidenceRepository(session)

        results = repository.latest_articles(EvidenceQuery(domains=["World and Geopolitics"], time_window="week"))

    assert results == []


def test_economic_observations_filter_by_series_and_region() -> None:
    with build_session() as session:
        seed_evidence(session)
        repository = ResearchEvidenceRepository(session)

        results = repository.economic_observations(EvidenceQuery(series_ids=["UNRATE"], regions=["US"], limit=5))

    assert len(results) == 1
    assert results[0].series_id == "UNRATE"
    assert results[0].display_name == "Unemployment Rate"
    assert results[0].description == "Share of the U.S. labor force that is unemployed."
    assert results[0].value == 4.3
    assert results[0].source_id == "fred-api"
    assert results[0].citation.title == "Unemployment Rate"


def test_economic_observations_match_state_abbreviation_to_state_name() -> None:
    now = datetime.now(UTC)

    with build_session() as session:
        seed_evidence(session)
        fred = session.scalar(select(Source).where(Source.name == "FRED API"))
        assert fred is not None
        session.add(
            EconomicObservation(
                source=fred,
                series_id="FHFA_HPI:STATE:AZ",
                series_name="FHFA All-Transactions HPI - Arizona",
                value=451.25,
                unit="index",
                period="2026Q2",
                released_at=now - timedelta(days=150),
                retrieved_at=now - timedelta(days=1),
                region="Arizona",
            )
        )
        session.commit()
        repository = ResearchEvidenceRepository(session)

        results = repository.economic_observations(
            EvidenceQuery(series_ids=["FHFA_HPI:*"], regions=["AZ"], time_window="quarter", limit=5)
        )

    assert len(results) == 1
    assert results[0].series_id == "FHFA_HPI:STATE:AZ"
    assert results[0].region == "Arizona"


def test_economic_observations_include_national_context_for_local_region() -> None:
    now = datetime.now(UTC)

    with build_session() as session:
        seed_evidence(session)
        fred = session.scalar(select(Source).where(Source.name == "FRED API"))
        assert fred is not None
        session.add_all(
            [
                EconomicObservation(
                    source=fred,
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
                    source=fred,
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
        repository = ResearchEvidenceRepository(session)

        results = repository.economic_observations(
            EvidenceQuery(
                series_ids=["FHFA_HPI:*", "FREDDIE_PMMS:*"],
                regions=["Phoenix"],
                time_window="quarter",
                limit=5,
            )
        )

    assert {result.series_id for result in results} == {"FHFA_HPI:METRO:38060", "FREDDIE_PMMS:30Y_FIXED"}
    assert results[0].region == "Phoenix-Mesa-Chandler, AZ"


def test_economic_observations_group_to_latest_per_series_and_region() -> None:
    now = datetime.now(UTC)

    with build_session() as session:
        seed_evidence(session)
        fred = session.scalar(select(Source).where(Source.name == "FRED API"))
        assert fred is not None
        session.add(
            EconomicObservation(
                source=fred,
                series_id="UNRATE",
                series_name="UNRATE",
                value=4.1,
                unit="percent",
                period="2026-07-01",
                released_at=now - timedelta(days=40),
                retrieved_at=now - timedelta(days=39),
                region="US",
            )
        )
        session.commit()
        repository = ResearchEvidenceRepository(session)

        results = repository.economic_observations(EvidenceQuery(series_ids=["UNRATE"], regions=["US"], limit=5))

    assert len(results) == 1
    assert results[0].period == "2026-08-01"


def test_source_health_returns_citation_ready_status() -> None:
    with build_session() as session:
        seed_evidence(session)
        repository = ResearchEvidenceRepository(session)

        results = repository.source_health(["bbc-news-rss"])

    assert len(results) == 1
    assert results[0].source_id == "bbc-news-rss"
    assert results[0].status == "fresh"
    assert results[0].latest_item_title == "Markets watch rate expectations"


def test_recent_ingestion_runs_filter_by_source() -> None:
    with build_session() as session:
        seed_evidence(session)
        repository = ResearchEvidenceRepository(session)

        results = repository.recent_ingestion_runs(["bbc-news-rss"], limit=5)

    assert len(results) == 1
    assert results[0].source_id == "bbc-news-rss"
    assert results[0].status == "success"
    assert results[0].items_inserted == 1
