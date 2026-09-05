from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Article, EconomicObservation, Report, Source
from app.db.session import get_db
from app.main import app
from app.services.suggestions import get_proactive_suggestions


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_context(session: Session) -> None:
    now = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    source = Source(
        name="Federal Reserve Economic Data",
        base_url="https://fred.stlouisfed.org",
        source_type="official_api",
        domains=["U.S. Economy and Policy", "Markets and Rates"],
        access_method="official_api",
        enabled=True,
    )
    session.add(source)
    session.flush()
    session.add(
        Article(
            source=source,
            title="Rates and technology shares move after labor data",
            url="https://example.com/rates-tech",
            publisher="Example News",
            published_at=now,
            retrieved_at=now,
            domains=["Markets and Rates", "Technology and AI"],
            tickers=["SPY", "QQQ"],
            companies=[],
            regions=["US"],
            storage_policy="metadata_only",
        )
    )
    session.add(
        EconomicObservation(
            source=source,
            series_id="MORTGAGE30US",
            series_name="30-Year Fixed Rate Mortgage Average",
            value=6.5,
            unit="percent",
            period="2026-09-03",
            released_at=now,
            retrieved_at=now,
            region="US",
        )
    )
    session.add(
        Report(
            report_type="market_strategy",
            status="generated",
            title="Market Strategy",
            summary="Markets are focused on rates.",
            body="This is not financial advice. Market scenario report.",
            domains=["Markets and Rates"],
            tickers=["SPY"],
            companies=[],
            as_of=now,
            confidence="medium",
            disclaimer_version="v1",
            guardrail_status="passed",
            report_metadata={"follow_up_questions": ["What changed in rates since the last report?"]},
        )
    )
    session.commit()


def test_proactive_suggestions_are_contextual_and_guarded() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        seed_context(session)

        response = get_proactive_suggestions(session)

        titles = {suggestion.title for suggestion in response.suggestions}
        prompts = " ".join(suggestion.prompt.lower() for suggestion in response.suggestions)

        assert response.total > 0
        assert "Generate Today's Briefing" in titles
        assert "Ask About Your Watchlist" in titles
        assert "Check Housing Conditions" in titles
        assert any("SPY" in suggestion.tickers for suggestion in response.suggestions)
        assert "buy" not in prompts
        assert "sell" not in prompts
        assert all("not financial advice" in suggestion.guardrail_note.lower() for suggestion in response.suggestions)


def test_proactive_suggestions_endpoint_returns_cards() -> None:
    session_factory = build_session_factory()

    def override_get_db():
        db = session_factory()
        try:
            seed_context(db)
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        response = client.get("/api/v1/suggestions/proactive?limit=3")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 3
        assert len(payload["suggestions"]) == 3
        assert payload["suggestions"][0]["guardrail_note"]
    finally:
        app.dependency_overrides.clear()
