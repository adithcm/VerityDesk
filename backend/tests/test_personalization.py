from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import UserSettings
from app.db.session import get_db
from app.main import app
from app.schemas.agent import AgentQueryRequest
from app.schemas.preferences import UserPreferencesUpdate
from app.services.personalization import personalize_agent_request, read_user_preferences, update_user_preferences


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_preferences_update_normalizes_and_persists_values() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        response = update_user_preferences(
            session,
            UserPreferencesUpdate(
                watchlist_tickers=["spy", "SPY", " qqq "],
                preferred_regions=[" Arizona ", "arizona", "Phoenix"],
                enabled_sources=["newsapi", "newsapi", "fred-api"],
            ),
        )
        stored = session.scalar(select(UserSettings))

    assert response.watchlist_tickers == ["SPY", "QQQ"]
    assert response.preferred_regions == ["Arizona", "Phoenix"]
    assert response.enabled_sources == ["newsapi", "fred-api"]
    assert stored is not None
    assert stored.watchlist_tickers == ["SPY", "QQQ"]


def test_personalize_agent_request_adds_saved_context_for_broad_query() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        update_user_preferences(
            session,
            UserPreferencesUpdate(
                watchlist_tickers=["AAPL", "MSFT"],
                preferred_regions=["Arizona"],
                enabled_sources=["newsapi", "fred-api"],
            ),
        )

        personalized = personalize_agent_request(
            AgentQueryRequest(user_query="What should I watch today?"),
            session,
        )

    assert personalized.tickers == ["AAPL", "MSFT"]
    assert personalized.source_ids == ["newsapi", "fred-api"]
    assert personalized.regions == []


def test_personalize_agent_request_adds_saved_region_for_housing_query() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        update_user_preferences(
            session,
            UserPreferencesUpdate(watchlist_tickers=["SPY"], preferred_regions=["Arizona"]),
        )

        personalized = personalize_agent_request(
            AgentQueryRequest(user_query="What is happening with housing?"),
            session,
        )

    assert personalized.regions == ["Arizona"]


def test_personalize_agent_request_does_not_override_explicit_fields() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        update_user_preferences(
            session,
            UserPreferencesUpdate(watchlist_tickers=["AAPL"], preferred_regions=["Arizona"]),
        )

        personalized = personalize_agent_request(
            AgentQueryRequest(
                user_query="What is happening with Tesla in Texas?",
                tickers=["TSLA"],
                regions=["Texas"],
            ),
            session,
        )

    assert personalized.tickers == ["TSLA"]
    assert personalized.regions == ["Texas"]


def test_preferences_endpoint_round_trip() -> None:
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
        auth_response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password123", "display_name": "Test User"},
        )
        token = auth_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        save_response = client.put(
            "/api/v1/preferences",
            headers=headers,
            json={
                "watchlist_tickers": ["spy"],
                "preferred_regions": ["Arizona"],
                "enabled_sources": ["newsapi"],
            },
        )
        read_response = client.get("/api/v1/preferences", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert auth_response.status_code == 200
    assert save_response.status_code == 200
    assert save_response.json()["watchlist_tickers"] == ["SPY"]
    assert read_response.status_code == 200
    assert read_response.json()["preferred_regions"] == ["Arizona"]


def test_read_user_preferences_creates_defaults() -> None:
    session_factory = build_session_factory()
    with session_factory() as session:
        response = read_user_preferences(session)

    assert response.watchlist_tickers == []
    assert response.preferred_regions == []
    assert response.enabled_sources == []
