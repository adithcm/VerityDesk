from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Report, UserSettings
from app.db.session import get_db
from app.main import app
from app.schemas.ingestion import DailyScheduleConfig, IngestionRunRequest, IngestionRunResponse
from app.schemas.report import ReportResponse
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
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    session_factory = build_session_factory()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    local_client = TestClient(app)
    schedule = {
        "enabled": True,
        "local_time": "07:30",
        "timezone": "America/Phoenix",
        "mode": "official_api",
        "generate_daily_briefing": True,
    }

    try:
        update_response = local_client.post("/api/v1/ingestion/schedule", json=schedule)
        get_response = local_client.get("/api/v1/ingestion/schedule")
    finally:
        app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert update_response.json() | schedule == update_response.json()
    assert get_response.json() | schedule == get_response.json()
    assert get_response.json()["next_run_at"] is not None


def test_schedule_config_persists_to_user_settings() -> None:
    with build_session() as session:
        updated = ingestion_runner.update_daily_schedule_config(
            session,
            DailyScheduleConfig(
                enabled=True,
                local_time="08:15",
                timezone="America/Phoenix",
                mode="rss",
                generate_daily_briefing=True,
            ),
        )
        loaded = ingestion_runner.get_daily_schedule_config(session)
        settings = session.scalar(select(UserSettings))

        assert settings is not None
        assert updated.enabled is True
        assert loaded.enabled is True
        assert loaded.local_time == "08:15"
        assert loaded.mode == "rss"
        assert loaded.generate_daily_briefing is True
        assert loaded.next_run_at is not None


def test_calculate_next_run_at_rolls_to_next_day() -> None:
    now = datetime(2026, 9, 5, 16, 30, tzinfo=UTC)

    next_run = ingestion_runner.calculate_next_run_at("08:00", "UTC", now)

    assert next_run == datetime(2026, 9, 6, 8, 0, tzinfo=UTC)


def test_run_due_daily_workflow_runs_ingestion_and_report(monkeypatch) -> None:
    with build_session() as session:
        ingestion_runner.update_daily_schedule_config(
            session,
            DailyScheduleConfig(
                enabled=True,
                local_time="08:00",
                timezone="UTC",
                mode="rss",
                generate_daily_briefing=True,
            ),
            now=datetime(2026, 9, 4, 7, 0, tzinfo=UTC),
        )

        def fake_run_ingestion(session_arg: Session, request: IngestionRunRequest) -> IngestionRunResponse:
            assert session_arg is session
            assert request.mode == "rss"
            return IngestionRunResponse(
                request_id="scheduled-run",
                mode=request.mode,
                status="success",
                started_at=datetime(2026, 9, 5, 8, 0, tzinfo=UTC).isoformat(),
                completed_at=datetime(2026, 9, 5, 8, 1, tzinfo=UTC).isoformat(),
                results=[],
                message="Scheduled ingestion complete.",
            )

        def fake_generate_daily_briefing(session_arg, request):
            report = Report(
                report_type="daily_briefing",
                status="generated",
                title=request.title or "Daily Briefing",
                summary="Summary",
                body="This is not financial advice. Scheduled briefing.",
                domains=[],
                tickers=[],
                companies=[],
                as_of=datetime(2026, 9, 5, 8, 1, tzinfo=UTC),
                confidence="medium",
                disclaimer_version="v1",
                guardrail_status="passed",
                report_metadata={},
            )
            session_arg.add(report)
            session_arg.commit()
            session_arg.refresh(report)
            return ReportResponse(
                id=report.id,
                report_type="daily_briefing",
                status="generated",
                title=report.title,
                summary=report.summary,
                body=report.body,
                domains=[],
                tickers=[],
                companies=[],
                as_of=report.as_of.isoformat(),
                confidence="medium",
                disclaimer_version="v1",
                guardrail_status="passed",
                metadata={},
                citations=[],
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat(),
            )

        monkeypatch.setattr(ingestion_runner, "run_ingestion", fake_run_ingestion)
        monkeypatch.setattr(ingestion_runner, "generate_daily_briefing", fake_generate_daily_briefing)

        status = ingestion_runner.run_due_daily_workflow(session, now=datetime(2026, 9, 5, 8, 5, tzinfo=UTC))

        assert status.last_status == "success"
        assert status.last_report_id is not None
        assert "Generated daily briefing" in (status.last_message or "")
        assert status.next_run_at is not None
