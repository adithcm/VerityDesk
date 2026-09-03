from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.main import app
from app.schemas.ingestion import DailyScheduleConfig, IngestionRunRequest, IngestionRunResponse
from app.services import ingestion_runner


client = TestClient(app)


@dataclass(frozen=True)
class FakeConfig:
    source_key: str


@dataclass(frozen=True)
class FakeResult:
    source_key: str
    status: str = "success"
    items_seen: int = 1
    items_inserted: int = 1
    items_updated: int = 0
    items_skipped: int = 0
    error: str | None = None


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def test_run_ingestion_runs_rss_and_official_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion_runner,
        "get_configured_rss_feeds",
        lambda: [FakeConfig("bbc-news-rss"), FakeConfig("sec-edgar-rss")],
    )
    monkeypatch.setattr(
        ingestion_runner,
        "get_configured_official_api_sources",
        lambda: [FakeConfig("sec-data-apis")],
    )
    monkeypatch.setattr(
        ingestion_runner,
        "ingest_rss_feed",
        lambda session, config: FakeResult(source_key=config.source_key),
    )
    monkeypatch.setattr(
        ingestion_runner,
        "ingest_official_api_source",
        lambda session, config: FakeResult(source_key=config.source_key, items_updated=2),
    )

    with build_session() as session:
        response = ingestion_runner.run_ingestion(session, IngestionRunRequest(mode="all"))

    assert response.status == "success"
    assert len(response.results) == 3
    assert {result.source_key for result in response.results} == {
        "bbc-news-rss",
        "sec-edgar-rss",
        "sec-data-apis",
    }
    assert "Completed 3 source runs" in response.message


def test_run_ingestion_filters_selected_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion_runner,
        "get_configured_rss_feeds",
        lambda: [FakeConfig("bbc-news-rss"), FakeConfig("sec-edgar-rss")],
    )
    monkeypatch.setattr(
        ingestion_runner,
        "ingest_rss_feed",
        lambda session, config: FakeResult(source_key=config.source_key),
    )

    with build_session() as session:
        response = ingestion_runner.run_ingestion(
            session,
            IngestionRunRequest(mode="rss", source_keys=["sec-edgar-rss"]),
        )

    assert response.status == "success"
    assert len(response.results) == 1
    assert response.results[0].source_key == "sec-edgar-rss"
    assert response.results[0].source_type == "rss"


def test_run_ingestion_reports_partial_success(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion_runner,
        "get_configured_rss_feeds",
        lambda: [FakeConfig("bbc-news-rss"), FakeConfig("sec-edgar-rss")],
    )

    def fake_ingest_rss(session, config):
        if config.source_key == "sec-edgar-rss":
            return FakeResult(source_key=config.source_key, status="failed", error="feed unavailable")
        return FakeResult(source_key=config.source_key)

    monkeypatch.setattr(ingestion_runner, "ingest_rss_feed", fake_ingest_rss)

    with build_session() as session:
        response = ingestion_runner.run_ingestion(session, IngestionRunRequest(mode="rss"))

    assert response.status == "partial_success"
    assert "failed sources 1" in response.message


def test_run_ingestion_returns_already_running_when_locked() -> None:
    acquired = ingestion_runner.run_lock.acquire(blocking=False)
    assert acquired is True

    try:
        with build_session() as session:
            response = ingestion_runner.run_ingestion(session, IngestionRunRequest(mode="all"))
    finally:
        ingestion_runner.run_lock.release()

    assert response.status == "already_running"
    assert response.results == []
    assert response.message == "An ingestion run is already in progress."


def test_trigger_ingestion_endpoint_returns_runner_response(monkeypatch) -> None:
    def fake_run_ingestion(session, request):
        return IngestionRunResponse(
            request_id="test-request",
            mode=request.mode,
            status="success",
            started_at=datetime(2026, 9, 2, 16, 0, tzinfo=UTC).isoformat(),
            completed_at=datetime(2026, 9, 2, 16, 1, tzinfo=UTC).isoformat(),
            results=[],
            message="No sources matched the ingestion request.",
        )

    monkeypatch.setattr("app.api.v1.endpoints.ingestion.run_ingestion", fake_run_ingestion)

    response = client.post("/api/v1/ingestion/run", json={"mode": "rss", "source_keys": ["bbc-news-rss"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "test-request"
    assert payload["mode"] == "rss"
    assert payload["status"] == "success"


def test_schedule_config_endpoint_round_trip() -> None:
    schedule = {
        "enabled": True,
        "local_time": "07:30",
        "timezone": "America/Phoenix",
        "mode": "official_api",
    }

    update_response = client.post("/api/v1/ingestion/schedule", json=schedule)
    get_response = client.get("/api/v1/ingestion/schedule")

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert update_response.json() == schedule
    assert get_response.json() == schedule

    ingestion_runner.update_daily_schedule_config(DailyScheduleConfig())
