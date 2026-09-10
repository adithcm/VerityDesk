from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Report
from app.db.session import get_db
from app.main import app
from app.schemas.watchlist import WatchItemCreate
from app.services.watchlist import create_watch_item, evaluate_watch_items, list_watch_items


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_watch_item_evaluation_creates_alert_once() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        create_watch_item(
            session,
            WatchItemCreate(
                title="Arizona affordability",
                category="housing",
                query="Tell me when Arizona affordability changes",
            ),
        )
        session.add(
            Report(
                report_type="housing",
                status="generated",
                title="Local Housing Pulse",
                summary="Arizona affordability is worsening as mortgage rates stay elevated.",
                body="Arizona affordability is worsening as mortgage rates stay elevated.",
                domains=["Housing and Real Estate"],
                tickers=[],
                companies=[],
                as_of=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
                confidence="medium",
                disclaimer_version="v1",
                guardrail_status="passed",
                report_metadata={"signal_label": "Developing", "change_label": "Worsening"},
            )
        )
        session.commit()

        first = evaluate_watch_items(session)
        second = evaluate_watch_items(session)
        listed = list_watch_items(session)

    assert first.checked == 1
    assert first.triggered == 1
    assert second.triggered == 0
    assert listed.items[0].status == "alert"
    assert "Arizona" in (listed.items[0].last_summary or "")


def test_watchlist_endpoint_round_trip() -> None:
    session_factory = build_session_factory()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        create_response = client.post(
            "/api/v1/watchlist/items",
            json={
                "title": "Fed cut odds",
                "category": "macro",
                "query": "Alert me if Fed cut odds change materially",
            },
        )
        list_response = client.get("/api/v1/watchlist/items")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["title"] == "Fed cut odds"
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
