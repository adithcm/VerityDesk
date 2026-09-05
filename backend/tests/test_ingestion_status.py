from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Article, EconomicObservation, IngestionRun, Source, SourceHealth
from app.main import app
from app.schemas.ingestion import (
    IngestionRunHistoryResponse,
    LatestItemsResponse,
    SourceHealthResponse,
)
from app.services import ingestion_status
from app.services.ingestion_status import get_source_health, list_ingestion_runs, list_latest_items


client = TestClient(app)


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def add_source(session, name: str = "FRED API") -> Source:
    source = Source(
        name=name,
        base_url="https://example.test",
        source_type="official_api",
        domains=["Markets and Rates"],
        access_method="api",
    )
    session.add(source)
    session.flush()
    return source


def test_get_source_health_includes_catalog_sources_and_calculates_stale() -> None:
    stale_time = datetime.now(UTC) - timedelta(hours=1)

    with build_session() as session:
        source = add_source(session)
        session.add(
            SourceHealth(
                source=source,
                source_key="fred-api",
                status="fresh",
                last_attempt_at=stale_time - timedelta(hours=1),
                last_success_at=stale_time - timedelta(hours=1),
                latest_item_title="Federal funds rate",
                freshness_window_hours=1,
                stale_after=stale_time,
            )
        )
        session.commit()

        response = get_source_health(session)

    fred = next(item for item in response.sources if item.source_key == "fred-api")
    bbc = next(item for item in response.sources if item.source_key == "bbc-news-rss")

    assert fred.status == "stale"
    assert fred.stored_status == "fresh"
    assert fred.source_name == "FRED API"
    assert fred.latest_item_title == "Federal funds rate"
    assert bbc.status == "not_configured"
    assert response.stale_count == 1
    assert response.not_configured_count >= 1


def test_get_source_health_preserves_failed_and_skipped_statuses() -> None:
    with build_session() as session:
        failed_source = add_source(session, name="BBC News RSS")
        skipped_source = add_source(session, name="U.S. Census Economic Indicators")
        session.add_all(
            [
                SourceHealth(
                    source=failed_source,
                    source_key="bbc-news-rss",
                    status="failed",
                    last_error="feed unavailable",
                ),
                SourceHealth(
                    source=skipped_source,
                    source_key="census-economic-indicators",
                    status="skipped",
                    last_error="Missing key",
                ),
            ]
        )
        session.commit()

        response = get_source_health(session)

    bbc = next(item for item in response.sources if item.source_key == "bbc-news-rss")
    census = next(item for item in response.sources if item.source_key == "census-economic-indicators")

    assert bbc.status == "failed"
    assert bbc.last_error == "feed unavailable"
    assert census.status == "skipped"
    assert census.last_error == "Missing key"
    assert response.failed_count == 1
    assert response.skipped_count == 1


def test_list_ingestion_runs_orders_recent_first() -> None:
    now = datetime(2026, 9, 3, 8, 0, tzinfo=UTC)

    with build_session() as session:
        source = add_source(session)
        session.add_all(
            [
                IngestionRun(
                    source=source,
                    source_key="fred-api",
                    run_type="manual",
                    status="success",
                    started_at=now - timedelta(hours=1),
                    completed_at=now - timedelta(minutes=55),
                    items_seen=3,
                    items_inserted=1,
                ),
                IngestionRun(
                    source=source,
                    source_key="fred-api",
                    run_type="manual",
                    status="success",
                    started_at=now,
                    completed_at=now + timedelta(minutes=1),
                    items_seen=4,
                    items_updated=4,
                ),
            ]
        )
        session.commit()

        response = list_ingestion_runs(session, limit=1)

    assert response.total == 1
    assert response.runs[0].items_seen == 4
    assert response.runs[0].source_name == "FRED API"


def test_list_latest_items_combines_articles_and_observations() -> None:
    now = datetime(2026, 9, 3, 8, 0, tzinfo=UTC)

    with build_session() as session:
        source = add_source(session)
        session.add_all(
            [
                Article(
                    source=source,
                    title="Markets update",
                    url="https://example.test/markets",
                    retrieved_at=now,
                    published_at=now - timedelta(minutes=30),
                    domains=["Markets and Rates"],
                    summary="Market metadata.",
                ),
                EconomicObservation(
                    source=source,
                    series_id="FEDFUNDS",
                    series_name="FEDFUNDS",
                    value=4.5,
                    unit="percent",
                    period="2026-08-01",
                    retrieved_at=now + timedelta(minutes=1),
                ),
            ]
        )
        session.commit()

        response = list_latest_items(session, limit=10)

    assert response.total == 2
    assert response.items[0].item_type == "economic_observation"
    assert response.items[0].title == "Federal Funds Rate"
    assert response.items[0].series_id == "FEDFUNDS"
    assert "Effective federal funds rate" in response.items[0].summary
    assert response.items[0].value == 4.5
    assert response.items[1].item_type == "article"
    assert response.items[1].url == "https://example.test/markets"


def test_list_latest_items_groups_observations_by_series_and_region() -> None:
    now = datetime(2026, 9, 3, 8, 0, tzinfo=UTC)

    with build_session() as session:
        source = add_source(session)
        session.add_all(
            [
                EconomicObservation(
                    source=source,
                    series_id="UNRATE",
                    series_name="UNRATE",
                    value=4.2,
                    unit="percent",
                    period="2026-07-01",
                    retrieved_at=now,
                    released_at=now - timedelta(days=30),
                    region="US",
                ),
                EconomicObservation(
                    source=source,
                    series_id="UNRATE",
                    series_name="UNRATE",
                    value=4.3,
                    unit="percent",
                    period="2026-08-01",
                    retrieved_at=now + timedelta(minutes=1),
                    released_at=now - timedelta(days=1),
                    region="US",
                ),
            ]
        )
        session.commit()

        response = list_latest_items(session, limit=10)

    assert response.total == 1
    assert response.items[0].title == "Unemployment Rate"
    assert response.items[0].period == "2026-08-01"


def test_ingestion_health_endpoint_returns_service_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.ingestion.get_source_health",
        lambda session: SourceHealthResponse(
            sources=[],
            total=0,
            fresh_count=0,
            stale_count=0,
            failed_count=0,
            skipped_count=0,
            not_configured_count=0,
        ),
    )

    response = client.get("/api/v1/ingestion/health")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_ingestion_runs_endpoint_returns_service_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.ingestion.list_ingestion_runs",
        lambda session, limit: IngestionRunHistoryResponse(runs=[], total=0),
    )

    response = client.get("/api/v1/ingestion/runs?limit=5")

    assert response.status_code == 200
    assert response.json() == {"runs": [], "total": 0}


def test_latest_items_endpoint_returns_service_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.ingestion.list_latest_items",
        lambda session, limit: LatestItemsResponse(items=[], total=0),
    )

    response = client.get("/api/v1/ingestion/latest-items?limit=5")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_calculate_freshness_status_treats_future_stale_after_as_fresh() -> None:
    health = SourceHealth(
        source_key="fred-api",
        status="fresh",
        last_attempt_at=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
        last_success_at=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
        stale_after=datetime(2026, 9, 3, 10, 0, tzinfo=UTC),
    )

    status = ingestion_status.calculate_freshness_status(
        health,
        now=datetime(2026, 9, 3, 9, 0, tzinfo=UTC),
    )

    assert status == "fresh"
