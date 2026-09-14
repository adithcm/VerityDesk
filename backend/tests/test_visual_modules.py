from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import EconomicObservation, Report, Source, SourceHealth, WatchItem
from app.db.session import get_db
from app.main import app
from app.services.visual_modules import get_visual_modules


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_get_visual_modules_builds_expected_contract() -> None:
    now = datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    session_factory = build_session_factory()

    with session_factory() as session:
        source = Source(
            name="FRED API",
            base_url="https://fred.stlouisfed.org",
            source_type="official_api",
            domains=["Markets and Rates", "Housing and Real Estate"],
            access_method="api",
        )
        session.add(source)
        session.flush()
        session.add_all(
            [
                SourceHealth(
                    source=source,
                    source_key="fred-api",
                    status="fresh",
                    last_success_at=now,
                    latest_item_title="30-year mortgage rate",
                ),
                EconomicObservation(
                    source=source,
                    series_id="MORTGAGE30US",
                    series_name="30-Year Fixed Rate Mortgage Average",
                    value=6.71,
                    unit="%",
                    period="2026-09-03",
                    retrieved_at=now,
                ),
                EconomicObservation(
                    source=source,
                    series_id="FEDFUNDS",
                    series_name="Federal Funds Rate",
                    value=4.5,
                    unit="%",
                    period="2026-08-01",
                    retrieved_at=now,
                ),
                Report(
                    report_type="daily_briefing",
                    status="generated",
                    title="Daily Brief",
                    summary="Markets and housing are the main signals today.",
                    body="Daily body.",
                    domains=["Markets and Rates"],
                    as_of=now,
                    confidence="medium",
                    guardrail_status="passed",
                ),
                WatchItem(title="Nvidia", category="company", query="NVDA", last_checked_at=now),
            ]
        )
        session.commit()

        response = get_visual_modules(session)

    modules = {module.id: module for module in response.modules}

    assert response.total == 5
    assert modules["daily_read"].related_report_id is not None
    assert modules["housing"].primary_value == "6.71%"
    assert modules["housing"].status == "ready"
    assert modules["macro"].primary_value == "4.5%"
    assert modules["companies"].primary_value == "1"
    assert modules["daily_read"].sources[0].name == "FRED API"


def test_visual_modules_endpoint_returns_modules() -> None:
    session_factory = build_session_factory()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        response = client.get("/api/v1/visuals/modules")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 5
    assert {module["id"] for module in response.json()["modules"]} == {
        "daily_read",
        "housing",
        "markets",
        "companies",
        "macro",
    }
