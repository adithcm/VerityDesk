from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from threading import Lock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserSettings
from app.schemas.ingestion import DailyScheduleConfig, IngestionRunRequest, IngestionRunResponse
from app.schemas.report import DailyBriefingRequest, HousingReportRequest, MacroReportRequest, MarketStrategyRequest
from app.services.official_api_ingestion import (
    OfficialAPIConfig,
    ingest_official_api_source,
    get_configured_official_api_sources,
)
from app.services.personalization import read_user_preferences
from app.services.reports import generate_daily_briefing, generate_housing_report, generate_macro_report, generate_market_strategy
from app.services.rss_ingestion import RSSFeedConfig, get_configured_rss_feeds, ingest_rss_feed


@dataclass(frozen=True)
class RunnerSourceResult:
    source_key: str
    source_type: str
    status: str
    items_seen: int
    items_inserted: int
    items_updated: int
    items_skipped: int
    error: str | None = None


run_lock = Lock()


def run_ingestion(session: Session, request: IngestionRunRequest) -> IngestionRunResponse:
    started_at = datetime.now(UTC)
    request_id = str(uuid4())

    if not run_lock.acquire(blocking=False):
        return already_running_response(request, request_id, started_at)

    try:
        return run_ingestion_without_lock(session, request, request_id, started_at)
    finally:
        run_lock.release()


def already_running_response(
    request: IngestionRunRequest,
    request_id: str | None = None,
    started_at: datetime | None = None,
) -> IngestionRunResponse:
    started = started_at or datetime.now(UTC)
    return IngestionRunResponse(
        request_id=request_id or str(uuid4()),
        mode=request.mode,
        status="already_running",
        started_at=started.isoformat(),
        completed_at=datetime.now(UTC).isoformat(),
        results=[],
        message="An ingestion run is already in progress.",
    )


def run_ingestion_without_lock(
    session: Session,
    request: IngestionRunRequest,
    request_id: str | None = None,
    started_at: datetime | None = None,
) -> IngestionRunResponse:
    started = started_at or datetime.now(UTC)
    results = run_selected_sources(session, request)
    completed_at = datetime.now(UTC)

    return IngestionRunResponse(
        request_id=request_id or str(uuid4()),
        mode=request.mode,
        status=overall_status(results),
        started_at=started.isoformat(),
        completed_at=completed_at.isoformat(),
        results=[result.__dict__ for result in results],
        message=build_run_message(results),
    )


def run_selected_sources(
    session: Session,
    request: IngestionRunRequest,
) -> list[RunnerSourceResult]:
    source_keys = set(request.source_keys)
    results: list[RunnerSourceResult] = []

    if request.mode in ("all", "rss"):
        rss_configs = filter_configs(get_configured_rss_feeds(), source_keys)
        for config in rss_configs:
            result = ingest_rss_feed(session, config)
            results.append(
                RunnerSourceResult(
                    source_key=result.source_key,
                    source_type="rss",
                    status=result.status,
                    items_seen=result.items_seen,
                    items_inserted=result.items_inserted,
                    items_updated=result.items_updated,
                    items_skipped=result.items_skipped,
                    error=result.error,
                )
            )

    if request.mode in ("all", "official_api"):
        official_configs = filter_configs(get_configured_official_api_sources(), source_keys)
        for config in official_configs:
            result = ingest_official_api_source(session, config)
            results.append(
                RunnerSourceResult(
                    source_key=result.source_key,
                    source_type="official_api",
                    status=result.status,
                    items_seen=result.items_seen,
                    items_inserted=result.items_inserted,
                    items_updated=result.items_updated,
                    items_skipped=result.items_skipped,
                    error=result.error,
                )
            )

    return results


def filter_configs(
    configs: list[RSSFeedConfig] | list[OfficialAPIConfig],
    source_keys: set[str],
) -> list[RSSFeedConfig] | list[OfficialAPIConfig]:
    if not source_keys:
        return configs

    return [config for config in configs if config.source_key in source_keys]


def overall_status(results: list[RunnerSourceResult]) -> str:
    if not results:
        return "success"

    failed_count = sum(result.status == "failed" for result in results)
    if failed_count == len(results):
        return "failed"

    if failed_count:
        return "partial_success"

    return "success"


def build_run_message(results: list[RunnerSourceResult]) -> str:
    if not results:
        return "No sources matched the ingestion request."

    inserted = sum(result.items_inserted for result in results)
    updated = sum(result.items_updated for result in results)
    failed = sum(result.status == "failed" for result in results)
    skipped = sum(result.status == "skipped" for result in results)

    return (
        f"Completed {len(results)} source runs. "
        f"Inserted {inserted}, updated {updated}, skipped sources {skipped}, failed sources {failed}."
    )


def get_daily_schedule_config(session: Session, now: datetime | None = None) -> DailyScheduleConfig:
    settings = get_or_create_user_settings(session)
    next_run_at = settings.daily_next_run_at or calculate_next_run_at(
        settings.daily_briefing_time or "08:00",
        settings.daily_schedule_timezone,
        now or datetime.now(UTC),
    )
    if not datetimes_match(settings.daily_next_run_at, next_run_at):
        settings.daily_next_run_at = next_run_at
        session.commit()
        session.refresh(settings)

    return settings_to_schedule_config(settings)


def update_daily_schedule_config(
    session: Session,
    config: DailyScheduleConfig,
    now: datetime | None = None,
) -> DailyScheduleConfig:
    settings = get_or_create_user_settings(session)
    settings.daily_schedule_enabled = config.enabled
    settings.daily_briefing_time = config.local_time
    settings.daily_schedule_timezone = config.timezone
    settings.daily_schedule_mode = config.mode
    settings.daily_report_enabled = config.generate_daily_briefing
    settings.daily_next_run_at = calculate_next_run_at(config.local_time, config.timezone, now or datetime.now(UTC))
    session.commit()
    session.refresh(settings)
    return settings_to_schedule_config(settings)


def run_due_daily_workflow(session: Session, now: datetime | None = None) -> DailyScheduleConfig:
    if not run_lock.acquire(blocking=False):
        return DailyScheduleConfig(
            last_status="already_running",
            last_message="Daily scheduler skipped this check because ingestion is already running.",
        )

    try:
        return run_due_daily_workflow_without_lock(session, now)
    finally:
        run_lock.release()


def run_due_daily_workflow_without_lock(session: Session, now: datetime | None = None) -> DailyScheduleConfig:
    current_time = now or datetime.now(UTC)
    settings = get_or_create_user_settings(session)
    if not settings.daily_schedule_enabled:
        next_run_at = calculate_next_run_at(
            settings.daily_briefing_time or "08:00",
            settings.daily_schedule_timezone,
            current_time,
        )
        if not datetimes_match(settings.daily_next_run_at, next_run_at):
            settings.daily_next_run_at = next_run_at
            session.commit()
            session.refresh(settings)
        return settings_to_schedule_config(settings)

    next_run_at = settings.daily_next_run_at or calculate_next_run_at(
        settings.daily_briefing_time or "08:00",
        settings.daily_schedule_timezone,
        current_time,
    )
    if current_time < as_aware_utc(next_run_at):
        if not datetimes_match(settings.daily_next_run_at, next_run_at):
            settings.daily_next_run_at = next_run_at
            session.commit()
            session.refresh(settings)
        return settings_to_schedule_config(settings)

    request = IngestionRunRequest(mode=settings.daily_schedule_mode, source_keys=[])
    response = run_ingestion_without_lock(session, request)
    report_id: int | None = None
    message = response.message

    if settings.daily_report_enabled:
        report_ids = generate_daily_topic_reports(session, current_time)
        report_id = report_ids[0] if report_ids else None
        message = f"{message} Generated {len(report_ids)} daily topic panel reports."

    completed_at = datetime.now(UTC)
    settings = get_or_create_user_settings(session)
    settings.daily_last_run_at = completed_at
    settings.daily_last_status = response.status
    settings.daily_last_message = message
    settings.daily_last_report_id = report_id
    settings.daily_next_run_at = calculate_next_run_at(
        settings.daily_briefing_time or "08:00",
        settings.daily_schedule_timezone,
        current_time + timedelta(days=1),
    )
    session.commit()
    session.refresh(settings)
    return settings_to_schedule_config(settings)


def generate_daily_topic_reports(session: Session, current_time: datetime) -> list[int]:
    preferences = read_user_preferences(session)
    date_label = current_time.date().isoformat()
    reports = [
        generate_daily_briefing(
            session,
            DailyBriefingRequest(
                title=f"Daily Briefing ({date_label})",
                time_window="day",
            ),
        ),
        generate_market_strategy(
            session,
            MarketStrategyRequest(
                title=f"Market Setup ({date_label})",
                tickers=preferences.watchlist_tickers,
                regions=preferences.preferred_regions,
                time_window="day",
                user_query=(
                    "Generate today's market setup as a daily topic panel. Focus on the highest-signal moves in "
                    "indexes, rates, yields, volatility, sectors, commodities, liquidity, and broad risk appetite. "
                    "Use concise Markdown with Bottom Line, What Changed, Major Trends, Why It Matters, and What To Watch."
                ),
            ),
        ),
        generate_housing_report(
            session,
            HousingReportRequest(
                title=f"Local Housing Pulse ({date_label})",
                regions=preferences.preferred_regions,
                time_window="day",
                user_query=(
                    "Generate today's local housing pulse as a daily topic panel. Focus on mortgage rates, affordability, "
                    "inventory, home prices, buyer/seller leverage, rent pressure, and local housing news. "
                    "Use concise Markdown with Bottom Line, What Changed, Major Trends, Why It Matters, and What To Watch."
                ),
            ),
        ),
        generate_macro_report(
            session,
            MacroReportRequest(
                title=f"Rates And Credit ({date_label})",
                regions=preferences.preferred_regions,
                time_window="day",
                user_query=(
                    "Generate today's rates and credit panel. Focus on rates, yields, inflation pressure, labor, "
                    "credit conditions, Fed policy signals, and consumer stress. Use concise Markdown with Bottom Line, "
                    "What Changed, Major Trends, Why It Matters, and What To Watch."
                ),
            ),
        ),
    ]
    return [report.id for report in reports]


def get_or_create_user_settings(session: Session) -> UserSettings:
    settings = session.scalar(select(UserSettings).order_by(UserSettings.id).limit(1))
    if settings is not None:
        return settings

    settings = UserSettings(
        watchlist_tickers=[],
        preferred_regions=[],
        enabled_sources=[],
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


def settings_to_schedule_config(settings: UserSettings) -> DailyScheduleConfig:
    return DailyScheduleConfig(
        enabled=settings.daily_schedule_enabled,
        local_time=settings.daily_briefing_time or "08:00",
        timezone=settings.daily_schedule_timezone,
        mode=settings.daily_schedule_mode,
        generate_daily_briefing=settings.daily_report_enabled,
        last_run_at=format_datetime(settings.daily_last_run_at),
        next_run_at=format_datetime(settings.daily_next_run_at),
        last_status=settings.daily_last_status,
        last_message=settings.daily_last_message,
        last_report_id=settings.daily_last_report_id,
    )


def calculate_next_run_at(local_time: str, timezone: str, now: datetime) -> datetime:
    hour, minute = parse_local_time(local_time)
    tzinfo = schedule_zoneinfo(timezone)
    local_now = as_aware_utc(now).astimezone(tzinfo)
    candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def parse_local_time(value: str) -> tuple[int, int]:
    hour_text, _, minute_text = value.partition(":")
    hour = int(hour_text)
    minute = int(minute_text or "0")
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("local_time must be a 24-hour HH:MM value")
    return hour, minute


def schedule_zoneinfo(timezone: str) -> ZoneInfo:
    if timezone == "local":
        return datetime.now().astimezone().tzinfo or UTC
    try:
        return ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return UTC


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def datetimes_match(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is right
    return as_aware_utc(left).replace(microsecond=0) == as_aware_utc(right).replace(microsecond=0)


def format_datetime(value: datetime | None) -> str | None:
    return as_aware_utc(value).isoformat() if value else None
