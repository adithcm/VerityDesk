from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import UserSettings
from app.services import auth


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_owner_account_gets_preloaded_profile(monkeypatch) -> None:
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(owner_email="owner@example.com"))
    session_factory = build_session_factory()

    with session_factory() as session:
        user, _token = auth.create_user(
            session,
            email="owner@example.com",
            password="password123",
            display_name="Owner",
        )
        settings = session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))

    assert user.setup_complete is True
    assert settings is not None
    assert settings.watchlist_tickers == ["SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
    assert settings.profile_metadata["location"] == "Phoenix, AZ"


def test_regular_account_starts_with_generic_setup_profile(monkeypatch) -> None:
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(owner_email="owner@example.com"))
    session_factory = build_session_factory()

    with session_factory() as session:
        user, _token = auth.create_user(
            session,
            email="new@example.com",
            password="password123",
            display_name="New User",
        )
        settings = session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))

    assert user.setup_complete is False
    assert settings is not None
    assert settings.watchlist_tickers == []
    assert settings.preferred_regions == []
    assert settings.profile_metadata["location"] == ""
