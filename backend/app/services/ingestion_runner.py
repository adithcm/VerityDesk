from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas.ingestion import DailyScheduleConfig, IngestionRunRequest, IngestionRunResponse
from app.services.official_api_ingestion import (
    OfficialAPIConfig,
    ingest_official_api_source,
    get_configured_official_api_sources,
)
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
daily_schedule_config = DailyScheduleConfig()


def run_ingestion(session: Session, request: IngestionRunRequest) -> IngestionRunResponse:
    started_at = datetime.now(UTC)
    request_id = str(uuid4())

    if not run_lock.acquire(blocking=False):
        return IngestionRunResponse(
            request_id=request_id,
            mode=request.mode,
            status="already_running",
            started_at=started_at.isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            results=[],
            message="An ingestion run is already in progress.",
        )

    try:
        results = run_selected_sources(session, request)
        completed_at = datetime.now(UTC)

        return IngestionRunResponse(
            request_id=request_id,
            mode=request.mode,
            status=overall_status(results),
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            results=[result.__dict__ for result in results],
            message=build_run_message(results),
        )
    finally:
        run_lock.release()


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


def get_daily_schedule_config() -> DailyScheduleConfig:
    return daily_schedule_config


def update_daily_schedule_config(config: DailyScheduleConfig) -> DailyScheduleConfig:
    global daily_schedule_config
    daily_schedule_config = config
    return daily_schedule_config
