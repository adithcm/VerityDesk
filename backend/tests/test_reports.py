from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Report
from app.db.session import get_db
from app.main import app
from app.schemas.report import ReportCreateRequest
from app.services.reports import create_report, delete_report, get_report, list_reports


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def build_session():
    return build_session_factory()()


def test_create_report_persists_shell_with_contract_fields() -> None:
    with build_session() as session:
        response = create_report(
            session,
            ReportCreateRequest(
                report_type="market_strategy",
                user_query="What matters for markets today?",
                domains=["Markets and Rates"],
                tickers=["spy"],
                time_window="week",
            ),
        )

        report = session.scalar(select(Report).where(Report.id == response.id))

        assert report is not None
        assert response.report_type == "market_strategy"
        assert response.status == "draft"
        assert response.confidence == "low"
        assert response.guardrail_status == "passed"
        assert response.tickers == ["SPY"]
        assert response.metadata["generation_stage"] == "contract_shell"
        assert "not financial advice" in response.body.lower()


def test_list_get_and_delete_reports() -> None:
    with build_session() as session:
        first = create_report(session, ReportCreateRequest(report_type="daily_briefing"))
        create_report(session, ReportCreateRequest(report_type="macro"))

        listed = list_reports(session, limit=10)
        filtered = list_reports(session, limit=10, report_type="daily_briefing")
        found = get_report(session, first.id)
        deleted = delete_report(session, first.id)

        assert listed.total == 2
        assert filtered.total == 1
        assert filtered.reports[0].report_type == "daily_briefing"
        assert found.id == first.id
        assert deleted.deleted is True
        assert session.get(Report, first.id) is None


def test_report_endpoints_create_list_read_delete() -> None:
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
        create_response = client.post(
            "/api/v1/reports",
            json={
                "report_type": "company_research",
                "title": "Apple Research",
                "tickers": ["aapl"],
                "companies": ["Apple"],
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()

        list_response = client.get("/api/v1/reports")
        read_response = client.get(f"/api/v1/reports/{created['id']}")
        delete_response = client.delete(f"/api/v1/reports/{created['id']}")
        missing_response = client.get(f"/api/v1/reports/{created['id']}")

        assert created["title"] == "Apple Research"
        assert created["tickers"] == ["AAPL"]
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1
        assert read_response.status_code == 200
        assert read_response.json()["id"] == created["id"]
        assert delete_response.status_code == 200
        assert delete_response.json() == {"id": created["id"], "deleted": True}
        assert missing_response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_report_endpoint_validates_report_type() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/reports", json={"report_type": "unsupported"})

    assert response.status_code == 422
