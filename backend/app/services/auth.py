from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserSession, UserSettings
from app.schemas.auth import AuthProfile, UserResponse
from app.services.personalization import get_or_create_preferences, preferences_to_response


SESSION_TTL_DAYS = 30
PASSWORD_ITERATIONS = 200_000


DEFAULT_PROFILE = AuthProfile(
    profile_name="Adith's intelligence desk",
    personal_note=(
        "Prioritize concise daily intelligence on world news, geopolitical news globally and in the U.S., "
        "major AI developments, major tech companies, S&P 500 conditions, and selected stock trends."
    ),
    location="Phoenix, AZ",
    housing_markets="Phoenix, Scottsdale, Tucson",
    watchlist="SPY, AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA",
    companies="Apple, Microsoft, Nvidia, Amazon, Alphabet, Meta, Tesla",
    priority_topics=["World news", "Geopolitics", "U.S. news", "AI and major tech", "Markets and watchlist"],
    sectors="AI, semiconductors, cloud, consumer technology, rates, housing",
    housing_interests=["Mortgage rates", "Affordability"],
    macro_interests=["Inflation", "Interest rates", "Fed policy"],
    risk_preference="balanced",
    investing_style="long_term",
    answer_format="brief",
    briefing_style="balanced",
    briefing_time="08:00",
)


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or "." not in normalized.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid email address")
    return normalized


def hash_password(password: str, salt: str | None = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${password_salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
    return hmac.compare_digest(digest, expected)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(session: Session, *, email: str, password: str, display_name: str) -> tuple[User, str]:
    normalized_email = normalize_email(email)
    existing = session.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for this email")

    user = User(
        email=normalized_email,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        setup_complete=True,
    )
    session.add(user)
    session.flush()
    seed_user_settings(session, user)
    token = create_session_token(session, user)
    session.commit()
    session.refresh(user)
    return user, token


def authenticate_user(session: Session, *, email: str, password: str) -> tuple[User, str]:
    normalized_email = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized_email))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")

    user.last_login_at = datetime.now(UTC)
    get_or_create_preferences(session, user)
    token = create_session_token(session, user)
    session.commit()
    session.refresh(user)
    return user, token


def create_session_token(session: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.add(
        UserSession(
            user=user,
            token_hash=hash_token(token),
            expires_at=now + timedelta(days=SESSION_TTL_DAYS),
            last_seen_at=now,
        )
    )
    return token


def current_user_from_authorization(session: Session, authorization: str | None) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login is required")
    token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(token)
    now = datetime.now(UTC)
    auth_session = session.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again")
    user = session.get(User, auth_session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session user is not active")
    auth_session.last_seen_at = now
    session.commit()
    return user


def require_user(authorization: str | None = Header(default=None)) -> str | None:
    return authorization


def revoke_token(session: Session, authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        return
    auth_session = session.scalar(select(UserSession).where(UserSession.token_hash == hash_token(authorization.removeprefix("Bearer ").strip())))
    if auth_session is not None:
        auth_session.revoked_at = datetime.now(UTC)
        session.commit()


def seed_user_settings(session: Session, user: User) -> UserSettings:
    settings = get_or_create_preferences(session, user)
    settings.watchlist_tickers = ["SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
    settings.preferred_regions = ["Phoenix, AZ", "Scottsdale, AZ", "Tucson, AZ", "United States"]
    settings.enabled_sources = []
    settings.daily_briefing_time = "08:00"
    settings.profile_metadata = DEFAULT_PROFILE.model_dump()
    return settings


def user_to_response(session: Session, user: User) -> UserResponse:
    settings = get_or_create_preferences(session, user)
    profile = AuthProfile(**(settings.profile_metadata or DEFAULT_PROFILE.model_dump()))
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        setup_complete=user.setup_complete,
        preferences=preferences_to_response(settings),
        profile=profile,
    )
