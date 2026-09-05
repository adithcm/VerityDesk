from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Article, EconomicObservation, IngestionRun, SourceHealth
from app.schemas.ingestion import (
    IngestionRunHistoryResponse,
    IngestionRunRecord,
    LatestIngestedItem,
    LatestItemsResponse,
    SourceHealthItem,
    SourceHealthResponse,
)
from app.services.economic_series import economic_series_info
from app.services.source_catalog import load_source_catalog


def get_source_health(session: Session) -> SourceHealthResponse:
    health_rows = {
        health.source_key: health
        for health in session.scalars(
            select(SourceHealth).options(joinedload(SourceHealth.source)).order_by(SourceHealth.source_key)
        )
    }

    items: list[SourceHealthItem] = []
    seen_keys: set[str] = set()

    for catalog_source in load_source_catalog():
        health = health_rows.get(catalog_source.id)
        seen_keys.add(catalog_source.id)
        items.append(build_source_health_item(catalog_source.id, catalog_source.name, health))

    for source_key, health in health_rows.items():
        if source_key in seen_keys:
            continue
        items.append(build_source_health_item(source_key, health.source.name if health.source else None, health))

    counts = {
        "fresh": sum(item.status == "fresh" for item in items),
        "stale": sum(item.status == "stale" for item in items),
        "failed": sum(item.status == "failed" for item in items),
        "skipped": sum(item.status == "skipped" for item in items),
        "not_configured": sum(item.status == "not_configured" for item in items),
    }

    return SourceHealthResponse(
        sources=items,
        total=len(items),
        fresh_count=counts["fresh"],
        stale_count=counts["stale"],
        failed_count=counts["failed"],
        skipped_count=counts["skipped"],
        not_configured_count=counts["not_configured"],
    )


def list_ingestion_runs(session: Session, *, limit: int = 50) -> IngestionRunHistoryResponse:
    runs = session.scalars(
        select(IngestionRun)
        .options(joinedload(IngestionRun.source))
        .order_by(desc(IngestionRun.started_at), desc(IngestionRun.id))
        .limit(limit)
    ).all()

    return IngestionRunHistoryResponse(
        runs=[
            IngestionRunRecord(
                id=run.id,
                source_key=run.source_key,
                source_name=run.source.name if run.source else None,
                run_type=run.run_type,
                status=run.status,
                started_at=format_datetime(run.started_at),
                completed_at=format_datetime(run.completed_at),
                items_seen=run.items_seen,
                items_inserted=run.items_inserted,
                items_updated=run.items_updated,
                items_skipped=run.items_skipped,
                error=run.error,
            )
            for run in runs
        ],
        total=len(runs),
    )


def list_latest_items(session: Session, *, limit: int = 25) -> LatestItemsResponse:
    source_key_by_name = {source.name: source.id for source in load_source_catalog()}
    articles = session.scalars(
        select(Article)
        .options(joinedload(Article.source))
        .order_by(desc(Article.retrieved_at), desc(Article.id))
        .limit(limit)
    ).all()

    observations = grouped_latest_observations(
        session.scalars(
            select(EconomicObservation)
            .options(joinedload(EconomicObservation.source))
            .order_by(
                desc(EconomicObservation.retrieved_at),
                desc(EconomicObservation.released_at),
                desc(EconomicObservation.id),
            )
            .limit(max(limit * 5, limit))
        ).all()
    )

    items = [article_to_latest_item(article, source_key_by_name) for article in articles] + [
        observation_to_latest_item(observation, source_key_by_name) for observation in observations
    ]
    items.sort(key=lambda item: item.retrieved_at or "", reverse=True)

    return LatestItemsResponse(items=items[:limit], total=min(len(items), limit))


def grouped_latest_observations(observations: list[EconomicObservation]) -> list[EconomicObservation]:
    latest_by_series_region: dict[tuple[str, str | None], EconomicObservation] = {}
    for observation in observations:
        key = (observation.series_id, observation.region)
        if key not in latest_by_series_region:
            latest_by_series_region[key] = observation

    return list(latest_by_series_region.values())


def build_source_health_item(
    source_key: str,
    source_name: str | None,
    health: SourceHealth | None,
) -> SourceHealthItem:
    if health is None:
        return SourceHealthItem(
            source_key=source_key,
            source_name=source_name,
            status="not_configured",
            stored_status=None,
        )

    return SourceHealthItem(
        source_key=source_key,
        source_name=source_name,
        status=calculate_freshness_status(health),
        stored_status=health.status,
        last_attempt_at=format_datetime(health.last_attempt_at),
        last_success_at=format_datetime(health.last_success_at),
        latest_item_published_at=format_datetime(health.latest_item_published_at),
        latest_item_title=health.latest_item_title,
        consecutive_failures=health.consecutive_failures,
        freshness_window_hours=health.freshness_window_hours,
        stale_after=format_datetime(health.stale_after),
        last_error=health.last_error,
    )


def calculate_freshness_status(health: SourceHealth, now: datetime | None = None) -> str:
    if health.status == "failed":
        return "failed"

    if health.status == "skipped":
        return "skipped"

    if health.last_attempt_at is None and health.last_success_at is None:
        return "not_configured"

    if health.stale_after is not None and as_aware_utc(health.stale_after) <= (now or datetime.now(UTC)):
        return "stale"

    return "fresh"


def article_to_latest_item(
    article: Article,
    source_key_by_name: dict[str, str],
) -> LatestIngestedItem:
    source_name = article.source.name if article.source else None
    return LatestIngestedItem(
        item_type="article",
        source_key=source_key_for_name(source_name, source_key_by_name),
        source_name=source_name,
        title=article.title,
        url=article.url,
        published_at=format_datetime(article.published_at),
        retrieved_at=format_datetime(article.retrieved_at),
        domains=article.domains,
        summary=article.summary,
    )


def observation_to_latest_item(
    observation: EconomicObservation,
    source_key_by_name: dict[str, str],
) -> LatestIngestedItem:
    source_name = observation.source.name if observation.source else None
    series_info = economic_series_info(observation.series_id, observation.series_name)
    unit = observation.unit or series_info.unit
    return LatestIngestedItem(
        item_type="economic_observation",
        source_key=source_key_for_name(source_name, source_key_by_name),
        source_name=source_name,
        series_id=observation.series_id,
        title=series_info.label,
        published_at=format_datetime(observation.released_at),
        retrieved_at=format_datetime(observation.retrieved_at),
        summary=build_observation_summary(observation, series_info.description, unit),
        value=observation.value,
        unit=unit,
        period=observation.period,
    )


def build_observation_summary(observation: EconomicObservation, description: str, unit: str | None) -> str:
    unit_label = f" {unit}" if unit else ""
    region = f" for {observation.region}" if observation.region else ""
    return f"{description} Latest value{region}: {observation.value}{unit_label} for {observation.period}."


def source_key_for_name(source_name: str | None, source_key_by_name: dict[str, str]) -> str:
    if source_name is None:
        return "unknown"
    return source_key_by_name.get(source_name, source_name)


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return as_aware_utc(value).isoformat()


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
