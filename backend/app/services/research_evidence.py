from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Article, EconomicObservation, IngestionRun, SourceHealth
from app.services.economic_series import economic_series_info
from app.services.ingestion_status import build_source_health_item
from app.services.region_normalization import expand_regions, region_match_values
from app.services.source_catalog import load_source_catalog


@dataclass(frozen=True)
class EvidenceCitation:
    source_id: str
    source_name: str | None
    title: str
    url: str | None
    published_at: str | None
    retrieved_at: str | None
    supports_claim: str


@dataclass(frozen=True)
class ArticleEvidence:
    id: int
    source_id: str
    source_name: str | None
    title: str
    url: str
    publisher: str | None
    published_at: str | None
    retrieved_at: str | None
    summary: str | None
    excerpt: str | None
    domains: list[str]
    tickers: list[str]
    companies: list[str]
    regions: list[str]
    citation: EvidenceCitation
    relevance_score: int


@dataclass(frozen=True)
class EconomicObservationEvidence:
    id: int
    source_id: str
    source_name: str | None
    series_id: str
    series_name: str
    display_name: str
    description: str
    value: float
    unit: str | None
    period: str
    released_at: str | None
    retrieved_at: str | None
    region: str | None
    citation: EvidenceCitation
    relevance_score: int


@dataclass(frozen=True)
class SourceHealthEvidence:
    source_id: str
    source_name: str | None
    status: str
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    latest_item_published_at: str | None = None
    latest_item_title: str | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class IngestionRunEvidence:
    source_id: str
    source_name: str | None
    run_type: str
    status: str
    started_at: str | None
    completed_at: str | None
    items_seen: int
    items_inserted: int
    items_updated: int
    items_skipped: int
    error: str | None


@dataclass(frozen=True)
class EvidenceQuery:
    domains: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    tickers: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    series_ids: list[str] = field(default_factory=list)
    time_window: str | None = None
    limit: int = 10


class ResearchEvidenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.source_key_by_name = {source.name: source.id for source in load_source_catalog()}

    def latest_articles(self, query: EvidenceQuery) -> list[ArticleEvidence]:
        articles = self.session.scalars(
            select(Article)
            .options(joinedload(Article.source))
            .order_by(desc(Article.published_at), desc(Article.retrieved_at), desc(Article.id))
            .limit(max(query.limit * 5, query.limit))
        ).all()

        filtered = [
            self.article_to_evidence(article, query)
            for article in articles
            if self.article_matches(article, query)
        ]
        return sorted(filtered, key=lambda item: item.relevance_score, reverse=True)[: query.limit]

    def economic_observations(self, query: EvidenceQuery) -> list[EconomicObservationEvidence]:
        statement = select(EconomicObservation).options(joinedload(EconomicObservation.source))

        series_filter = observation_series_filter(query.series_ids)
        if series_filter is not None:
            statement = statement.where(series_filter)

        region_filter = observation_region_filter(query.regions)
        if region_filter is not None:
            statement = statement.where(region_filter)

        observations = self.session.scalars(
            statement.order_by(
                desc(EconomicObservation.released_at),
                desc(EconomicObservation.retrieved_at),
                desc(EconomicObservation.id),
            ).limit(max(query.limit * 25, 250))
        ).all()

        filtered = [
            self.observation_to_evidence(observation, query)
            for observation in observations
            if self.observation_matches(observation, query)
        ]
        grouped = group_latest_observation_evidence(filtered)
        return sorted(grouped, key=lambda item: item.relevance_score, reverse=True)[: query.limit]

    def source_health(self, source_ids: list[str] | None = None) -> list[SourceHealthEvidence]:
        selected_source_ids = normalize_values(source_ids or [])
        health_rows = self.session.scalars(
            select(SourceHealth).options(joinedload(SourceHealth.source)).order_by(SourceHealth.source_key)
        ).all()

        evidence = [
            self.health_to_evidence(health)
            for health in health_rows
            if not selected_source_ids or normalize_value(health.source_key) in selected_source_ids
        ]
        return evidence

    def recent_ingestion_runs(self, source_ids: list[str] | None = None, *, limit: int = 10) -> list[IngestionRunEvidence]:
        selected_source_ids = normalize_values(source_ids or [])
        runs = self.session.scalars(
            select(IngestionRun)
            .options(joinedload(IngestionRun.source))
            .order_by(desc(IngestionRun.started_at), desc(IngestionRun.id))
            .limit(max(limit * 5, limit))
        ).all()

        evidence = [
            self.run_to_evidence(run)
            for run in runs
            if not selected_source_ids or normalize_value(run.source_key) in selected_source_ids
        ]
        return evidence[:limit]

    def article_matches(self, article: Article, query: EvidenceQuery) -> bool:
        if not within_time_window(article.published_at or article.retrieved_at, query.time_window):
            return False

        return (
            matches_any(article.domains, query.domains)
            and matches_source(self.source_id_for_article(article), query.source_ids)
            and matches_any(article.tickers, query.tickers)
            and matches_any(article.companies, query.companies)
            and matches_regions(article.regions, query.regions)
        )

    def observation_matches(self, observation: EconomicObservation, query: EvidenceQuery) -> bool:
        if not within_time_window(latest_datetime(observation.released_at, observation.retrieved_at), query.time_window):
            return False

        return (
            matches_source(self.source_id_for_observation(observation), query.source_ids)
            and matches_series_id(observation.series_id, query.series_ids)
            and matches_regions([observation.region] if observation.region else [], query.regions)
        )

    def article_to_evidence(self, article: Article, query: EvidenceQuery) -> ArticleEvidence:
        source_id = self.source_id_for_article(article)
        source_name = article.source.name if article.source else None
        relevance_score = score_article(article, query)
        return ArticleEvidence(
            id=article.id,
            source_id=source_id,
            source_name=source_name,
            title=article.title,
            url=article.url,
            publisher=article.publisher,
            published_at=format_datetime(article.published_at),
            retrieved_at=format_datetime(article.retrieved_at),
            summary=article.summary,
            excerpt=article.excerpt,
            domains=article.domains,
            tickers=article.tickers,
            companies=article.companies,
            regions=article.regions,
            citation=EvidenceCitation(
                source_id=source_id,
                source_name=source_name,
                title=article.title,
                url=article.url,
                published_at=format_datetime(article.published_at),
                retrieved_at=format_datetime(article.retrieved_at),
                supports_claim="Article evidence retrieved for the agent query.",
            ),
            relevance_score=relevance_score,
        )

    def observation_to_evidence(
        self,
        observation: EconomicObservation,
        query: EvidenceQuery,
    ) -> EconomicObservationEvidence:
        source_id = self.source_id_for_observation(observation)
        source_name = observation.source.name if observation.source else None
        series_info = economic_series_info(observation.series_id, observation.series_name)
        relevance_score = score_observation(observation, query)
        return EconomicObservationEvidence(
            id=observation.id,
            source_id=source_id,
            source_name=source_name,
            series_id=observation.series_id,
            series_name=observation.series_name,
            display_name=series_info.label,
            description=series_info.description,
            value=observation.value,
            unit=observation.unit or series_info.unit,
            period=observation.period,
            released_at=format_datetime(observation.released_at),
            retrieved_at=format_datetime(observation.retrieved_at),
            region=observation.region,
            citation=EvidenceCitation(
                source_id=source_id,
                source_name=source_name,
                title=series_info.label,
                url=None,
                published_at=format_datetime(observation.released_at),
                retrieved_at=format_datetime(observation.retrieved_at),
                supports_claim="Economic observation evidence retrieved for the agent query.",
            ),
            relevance_score=relevance_score,
        )

    def health_to_evidence(self, health: SourceHealth) -> SourceHealthEvidence:
        item = build_source_health_item(
            health.source_key,
            health.source.name if health.source else None,
            health,
        )
        return SourceHealthEvidence(
            source_id=item.source_key,
            source_name=item.source_name,
            status=item.status,
            last_attempt_at=item.last_attempt_at,
            last_success_at=item.last_success_at,
            latest_item_published_at=item.latest_item_published_at,
            latest_item_title=item.latest_item_title,
            last_error=item.last_error,
        )

    def run_to_evidence(self, run: IngestionRun) -> IngestionRunEvidence:
        return IngestionRunEvidence(
            source_id=run.source_key,
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

    def source_id_for_article(self, article: Article) -> str:
        if article.source is None:
            return "unknown"
        return self.source_key_by_name.get(article.source.name, article.source.name)

    def source_id_for_observation(self, observation: EconomicObservation) -> str:
        if observation.source is None:
            return "unknown"
        return self.source_key_by_name.get(observation.source.name, observation.source.name)


def matches_any(values: list[str], filters: list[str]) -> bool:
    normalized_filters = normalize_values(filters)
    if not normalized_filters:
        return True

    normalized_values = normalize_values(values)
    return any(value in normalized_values for value in normalized_filters)


def matches_regions(values: list[str], filters: list[str]) -> bool:
    expanded_filters = expand_regions(filters)
    if not expanded_filters:
        return True

    normalized_filters = {value for region in expanded_filters for value in region_match_values(region)}
    normalized_values = {value for region in values for value in region_match_values(region)}
    return bool(normalized_filters & normalized_values)


def matches_series_id(series_id: str, filters: list[str]) -> bool:
    normalized_filters = normalize_values(filters)
    if not normalized_filters:
        return True

    normalized_series = normalize_value(series_id)
    for filter_value in normalized_filters:
        if filter_value.endswith("*") and normalized_series.startswith(filter_value[:-1]):
            return True
        if normalized_series == filter_value:
            return True
    return False


def observation_series_filter(filters: list[str]):
    normalized_filters = normalize_values(filters)
    if not normalized_filters:
        return None

    conditions = []
    for filter_value in normalized_filters:
        if filter_value.endswith("*"):
            conditions.append(func.lower(EconomicObservation.series_id).like(f"{filter_value[:-1]}%"))
        else:
            conditions.append(func.lower(EconomicObservation.series_id) == filter_value)
    return or_(*conditions)


def observation_region_filter(filters: list[str]):
    expanded_filters = expand_regions(filters)
    if not expanded_filters:
        return None

    normalized_regions = {
        normalize_region
        for region in expanded_filters
        for normalize_region in region_match_values(region)
    }
    if not normalized_regions:
        return None

    return func.lower(EconomicObservation.region).in_(normalized_regions)


def matches_source(source_id: str, source_ids: list[str]) -> bool:
    normalized_source_ids = normalize_values(source_ids)
    if not normalized_source_ids:
        return True

    return normalize_value(source_id) in normalized_source_ids


def score_article(article: Article, query: EvidenceQuery) -> int:
    score = 0
    score += 3 * overlap_count(article.domains, query.domains)
    score += 4 * overlap_count(article.tickers, query.tickers)
    score += 4 * overlap_count(article.companies, query.companies)
    score += 2 * region_overlap_count(article.regions, query.regions)
    score += 1 if article.summary else 0
    score += 1 if article.excerpt else 0
    return score


def score_observation(observation: EconomicObservation, query: EvidenceQuery) -> int:
    score = 0
    score += 5 if matches_series_id(observation.series_id, query.series_ids) and query.series_ids else 0
    score += 3 * region_overlap_count([observation.region] if observation.region else [], query.regions)
    if query.regions and observation.region and normalize_value(observation.region) in {"us", "usa", "united states", "us market"}:
        score -= 1
    return score


def group_latest_observation_evidence(
    observations: list[EconomicObservationEvidence],
) -> list[EconomicObservationEvidence]:
    grouped: dict[tuple[str, str | None], EconomicObservationEvidence] = {}
    for observation in observations:
        key = (observation.series_id, observation.region)
        existing = grouped.get(key)
        if existing is None or observation_sort_key(observation) > observation_sort_key(existing):
            grouped[key] = observation

    return list(grouped.values())


def observation_sort_key(observation: EconomicObservationEvidence) -> tuple[str, str]:
    return (observation.released_at or "", observation.retrieved_at or "")


def overlap_count(values: list[str], filters: list[str]) -> int:
    if not filters:
        return 0

    normalized_values = normalize_values(values)
    return sum(value in normalized_values for value in normalize_values(filters))


def region_overlap_count(values: list[str], filters: list[str]) -> int:
    expanded_filters = expand_regions(filters)
    if not expanded_filters:
        return 0

    normalized_filters = {value for region in expanded_filters for value in region_match_values(region)}
    return sum(bool(region_match_values(value) & normalized_filters) for value in values if value)


def latest_datetime(*values: datetime | None) -> datetime | None:
    present = [as_aware_utc(value) for value in values if value is not None]
    return max(present) if present else None


def within_time_window(value: datetime | None, time_window: str | None) -> bool:
    if value is None or not time_window:
        return True

    lower_bound = datetime.now(UTC) - time_delta_for_window(time_window)
    return as_aware_utc(value) >= lower_bound


def time_delta_for_window(time_window: str) -> timedelta:
    normalized = normalize_value(time_window)
    if normalized in {"today", "24h", "1d", "daily"}:
        return timedelta(days=1)
    if normalized in {"week", "7d", "weekly"}:
        return timedelta(days=7)
    if normalized in {"month", "30d", "monthly"}:
        return timedelta(days=30)
    if normalized in {"quarter", "90d", "quarterly"}:
        return timedelta(days=90)
    return timedelta(days=30)


def normalize_values(values: list[str]) -> set[str]:
    return {normalize_value(value) for value in values if value}


def normalize_value(value: str) -> str:
    return value.strip().lower()


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return as_aware_utc(value).isoformat()


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
