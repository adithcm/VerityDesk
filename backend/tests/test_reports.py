from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Report, Source
from app.db.session import get_db
from app.main import app
from app.schemas.agent import AgentCitation, AgentQueryResponse, GuardrailCheck
from app.schemas.report import ReportCreateRequest
from app.services import reports
from app.services.reports import (
    create_report,
    delete_report,
    generate_company_research,
    generate_daily_briefing,
    get_report,
    list_reports,
)


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


def test_generate_daily_briefing_saves_agent_response_and_citations(monkeypatch) -> None:
    def fake_run_agent_query(request, session):
        return AgentQueryResponse(
            request_id="agent-request-1",
            summary=(
                "This is not financial advice. InvestorAgent is for research and educational purposes only.\n\n"
                "Markets are focused on rates and labor data today."
            ),
            agents_ran=["CoordinatorAgent", "NewsDigestAgent", "MarketAgent", "SynthesisAgent"],
            claims=[],
            citations=[
                AgentCitation(
                    source_id="BBC News RSS",
                    title="Markets watch rates",
                    url="https://example.test/markets",
                    publisher="BBC",
                    published_at="2026-09-04T12:00:00+00:00",
                    retrieved_at="2026-09-04T13:00:00+00:00",
                    supports_claim="Markets focused on rates.",
                )
            ],
            confidence="medium",
            risks=["Evidence may be incomplete."],
            follow_up_questions=["Should we narrow this by sector?"],
            guardrail=GuardrailCheck(
                status="passed",
                disclaimer="This is not financial advice.",
                issues=[],
                banned_phrases_found=[],
                required_sections=[],
            ),
            requires_guardrail_review=False,
        )

    monkeypatch.setattr(reports, "run_agent_query", fake_run_agent_query)

    with build_session() as session:
        session.add(
            Source(
                name="BBC News RSS",
                base_url="https://www.bbc.com/news",
                source_type="official_rss",
                domains=["Markets and Rates"],
                access_method="rss",
            )
        )
        session.commit()

        response = generate_daily_briefing(session, reports.DailyBriefingRequest())

        assert response.report_type == "daily_briefing"
        assert response.status == "generated"
        assert response.confidence == "medium"
        assert response.guardrail_status == "passed"
        assert response.metadata["generation_stage"] == "daily_briefing"
        assert response.metadata["agent_request_id"] == "agent-request-1"
        assert response.summary == "Markets are focused on rates and labor data today."
        assert len(response.citations) == 1
        assert response.citations[0].title == "Markets watch rates"


def test_daily_briefing_endpoint_returns_generated_report(monkeypatch) -> None:
    def fake_generate_daily_briefing(session, request):
        return reports.ReportResponse(
            id=1,
            report_type="daily_briefing",
            status="generated",
            title=request.title or "Daily Briefing",
            summary="Briefing summary.",
            body="Briefing body.",
            domains=request.domains,
            tickers=[],
            companies=[],
            as_of="2026-09-04T12:00:00+00:00",
            confidence="medium",
            disclaimer_version="v1",
            guardrail_status="passed",
            metadata={"generation_stage": "daily_briefing"},
            citations=[],
            created_at="2026-09-04T12:00:00+00:00",
            updated_at="2026-09-04T12:00:00+00:00",
        )

    monkeypatch.setattr("app.api.v1.endpoints.reports.generate_daily_briefing", fake_generate_daily_briefing)

    response = TestClient(app).post(
        "/api/v1/reports/daily-briefing",
        json={"title": "Morning Briefing", "domains": ["Markets and Rates"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Morning Briefing"
    assert payload["status"] == "generated"


def test_generate_company_research_saves_agent_response_and_citations(monkeypatch) -> None:
    def fake_run_agent_query(request, session):
        assert request.intent == "company_research"
        assert request.tickers == ["AAPL"]
        assert request.companies == ["Apple"]
        return AgentQueryResponse(
            request_id="company-agent-request-1",
            summary=(
                "This is not financial advice. InvestorAgent is for research and educational purposes only.\n\n"
                "Apple research is focused on filings, demand, and margin context."
            ),
            agents_ran=["CoordinatorAgent", "CompanyAgent", "MarketAgent", "SynthesisAgent"],
            claims=[],
            citations=[
                AgentCitation(
                    source_id="SEC EDGAR RSS",
                    title="Apple filing",
                    url="https://example.test/aapl",
                    publisher="SEC",
                    published_at="2026-09-04T12:00:00+00:00",
                    retrieved_at="2026-09-04T13:00:00+00:00",
                    supports_claim="Apple filed a company update.",
                )
            ],
            confidence="medium",
            risks=["Company evidence may be incomplete."],
            follow_up_questions=["Should we compare this with prior filings?"],
            guardrail=GuardrailCheck(
                status="passed",
                disclaimer="This is not financial advice.",
                issues=[],
                banned_phrases_found=[],
                required_sections=[],
            ),
            requires_guardrail_review=False,
        )

    monkeypatch.setattr(reports, "run_agent_query", fake_run_agent_query)

    with build_session() as session:
        session.add(
            Source(
                name="SEC EDGAR RSS",
                base_url="https://www.sec.gov",
                source_type="official_rss",
                domains=["Companies and Earnings"],
                access_method="rss",
            )
        )
        session.commit()

        response = generate_company_research(
            session,
            reports.CompanyResearchRequest(ticker="aapl", company="Apple"),
        )

        assert response.report_type == "company_research"
        assert response.status == "generated"
        assert response.tickers == ["AAPL"]
        assert response.companies == ["Apple"]
        assert response.metadata["generation_stage"] == "company_research"
        assert response.metadata["agent_request_id"] == "company-agent-request-1"
        assert response.summary == "Apple research is focused on filings, demand, and margin context."
        assert len(response.citations) == 1
        assert response.citations[0].title == "Apple filing"


def test_company_research_endpoint_returns_generated_report(monkeypatch) -> None:
    def fake_generate_company_research(session, request):
        return reports.ReportResponse(
            id=2,
            report_type="company_research",
            status="generated",
            title=request.title or "Company Research",
            summary="Company summary.",
            body="Company body.",
            domains=request.domains,
            tickers=["AAPL"],
            companies=["Apple"],
            as_of="2026-09-04T12:00:00+00:00",
            confidence="medium",
            disclaimer_version="v1",
            guardrail_status="passed",
            metadata={"generation_stage": "company_research"},
            citations=[],
            created_at="2026-09-04T12:00:00+00:00",
            updated_at="2026-09-04T12:00:00+00:00",
        )

    monkeypatch.setattr("app.api.v1.endpoints.reports.generate_company_research", fake_generate_company_research)

    response = TestClient(app).post(
        "/api/v1/reports/company-research",
        json={"ticker": "aapl", "company": "Apple"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["report_type"] == "company_research"
    assert payload["tickers"] == ["AAPL"]


def test_company_research_endpoint_requires_ticker_or_company() -> None:
    response = TestClient(app).post("/api/v1/reports/company-research", json={})

    assert response.status_code == 422


def test_report_endpoint_validates_report_type() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/reports", json={"report_type": "unsupported"})

    assert response.status_code == 422
