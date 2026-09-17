from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserSettings
from app.schemas.agent import AgentQueryRequest
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate


BROAD_PERSONALIZATION_TERMS = {
    "briefing",
    "my",
    "portfolio",
    "what should i watch",
    "what to watch",
    "watchlist",
    "companies i follow",
    "companies i track",
    "tickers i follow",
    "tickers i track",
}

HOUSING_TERMS = {"housing", "home", "mortgage", "real estate", "rent", "rental"}
SPECIFIC_COMPANY_TERMS = {
    "alphabet",
    "amazon",
    "apple",
    "google",
    "meta",
    "microsoft",
    "nvidia",
    "tesla",
}


def get_or_create_preferences(session: Session, user: User | None = None) -> UserSettings:
    if user is not None:
        settings = session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        if settings is not None:
            return settings
        settings = UserSettings(
            user_id=user.id,
            watchlist_tickers=[],
            preferred_regions=[],
            enabled_sources=[],
            profile_metadata={},
            daily_briefing_time="08:00",
            daily_schedule_enabled=False,
            daily_schedule_timezone="local",
            daily_schedule_mode="all",
            daily_report_enabled=False,
        )
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings

    settings = session.scalar(select(UserSettings).where(UserSettings.user_id.is_(None)).order_by(UserSettings.id).limit(1))
    if settings is not None:
        return settings

    settings = UserSettings(
        watchlist_tickers=[],
        preferred_regions=[],
        enabled_sources=[],
        profile_metadata={},
        daily_briefing_time="08:00",
        daily_schedule_enabled=False,
        daily_schedule_timezone="local",
        daily_schedule_mode="all",
        daily_report_enabled=False,
    )
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def read_user_preferences(session: Session, user: User | None = None) -> UserPreferencesResponse:
    return preferences_to_response(get_or_create_preferences(session, user))


def update_user_preferences(
    session: Session,
    update: UserPreferencesUpdate,
    user: User | None = None,
) -> UserPreferencesResponse:
    settings = get_or_create_preferences(session, user)
    if update.watchlist_tickers is not None:
        settings.watchlist_tickers = normalize_tickers(update.watchlist_tickers)
    if update.preferred_regions is not None:
        settings.preferred_regions = dedupe_clean_values(update.preferred_regions)
    if update.enabled_sources is not None:
        settings.enabled_sources = dedupe_clean_values(update.enabled_sources)

    session.commit()
    session.refresh(settings)
    return preferences_to_response(settings)


def personalize_agent_request(
    request: AgentQueryRequest,
    session: Session,
    user: User | None = None,
) -> AgentQueryRequest:
    settings = get_or_create_preferences(session, user)
    updates: dict[str, list[str]] = {}
    text = request.user_query.lower()

    if not request.tickers and should_apply_watchlist(text, request):
        updates["tickers"] = normalize_tickers(settings.watchlist_tickers)

    if not request.regions and should_apply_regions(text, request):
        updates["regions"] = dedupe_clean_values(settings.preferred_regions)

    if not request.source_ids and settings.enabled_sources:
        updates["source_ids"] = dedupe_clean_values(settings.enabled_sources)

    if updates:
        return request.model_copy(update={key: value for key, value in updates.items() if value})
    return request


def should_apply_watchlist(text: str, request: AgentQueryRequest) -> bool:
    if request.companies:
        return False
    if any(term in text for term in SPECIFIC_COMPANY_TERMS):
        return False
    if request.intent == "daily_briefing":
        return True
    return any(term in text for term in BROAD_PERSONALIZATION_TERMS)


def should_apply_regions(text: str, request: AgentQueryRequest) -> bool:
    if request.intent in {"daily_briefing", "housing_macro_research"}:
        return True
    if any(term in text for term in HOUSING_TERMS):
        return True
    return "my area" in text or "near me" in text


def preferences_to_response(settings: UserSettings) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        watchlist_tickers=normalize_tickers(settings.watchlist_tickers or []),
        preferred_regions=dedupe_clean_values(settings.preferred_regions or []),
        enabled_sources=dedupe_clean_values(settings.enabled_sources or []),
    )


def normalize_tickers(values: list[str]) -> list[str]:
    return [value.upper() for value in dedupe_clean_values(values)]


def dedupe_clean_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        text = value.strip()
        normalized = text.lower()
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(text)
    return cleaned
