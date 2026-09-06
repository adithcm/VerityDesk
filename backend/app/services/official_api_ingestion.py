import json
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import Article, EconomicObservation, ExternalID, IngestionRun, Source, SourceHealth
from app.schemas.source import SourceCatalogEntry
from app.services.source_catalog import load_source_catalog


ConnectorKind = Literal[
    "sec_submissions",
    "fred_observations",
    "census_eits",
    "fhfa_placeholder",
    "freddie_mac_placeholder",
]


@dataclass(frozen=True)
class OfficialAPIConfig:
    source_key: str
    source_name: str
    base_url: str | None
    endpoint_url: str | None
    domains: tuple[str, ...]
    source_type: str
    access_method: str
    update_cadence: str
    reliability_tier: str
    storage_policy: str
    enabled: bool
    connector_kind: ConnectorKind
    required_api_key_setting: str | None = None
    default_identifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class OfficialIngestionResult:
    source_key: str
    status: str
    items_seen: int
    items_inserted: int
    items_updated: int
    items_skipped: int
    error: str | None = None


@dataclass(frozen=True)
class SECSubmissionRecord:
    source_key: str
    cik: str
    company_name: str
    accession_number: str
    form: str
    filing_date: str | None
    report_date: str | None
    primary_document: str | None
    description: str | None
    url: str
    retrieved_at: datetime
    domains: list[str]
    storage_policy: str

    @property
    def title(self) -> str:
        return f"{self.form} - {self.company_name}"

    @property
    def content_hash(self) -> str:
        raw = "|".join(
            [
                self.source_key,
                self.cik,
                self.accession_number,
                self.form,
                self.filing_date or "",
                self.report_date or "",
                self.primary_document or "",
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StructuredObservationRecord:
    source_key: str
    series_id: str
    series_name: str
    value: float
    unit: str | None
    period: str
    released_at: datetime | None
    retrieved_at: datetime
    vintage: str | None = None
    region: str | None = None
    external_id: str | None = None


def get_configured_official_api_sources() -> list[OfficialAPIConfig]:
    catalog_by_id = {source.id: source for source in load_source_catalog()}

    return [
        build_official_api_config(
            catalog_by_id["sec-data-apis"],
            connector_kind="sec_submissions",
            endpoint_url="https://data.sec.gov/submissions/CIK{identifier}.json",
            default_identifiers=("0000320193",),
        ),
        build_official_api_config(
            catalog_by_id["fred-api"],
            connector_kind="fred_observations",
            endpoint_url="https://api.stlouisfed.org/fred/series/observations",
            required_api_key_setting="fred_api_key",
            default_identifiers=("FEDFUNDS", "MORTGAGE30US", "UNRATE"),
        ),
        build_official_api_config(
            catalog_by_id["census-economic-indicators"],
            connector_kind="census_eits",
            endpoint_url="https://api.census.gov/data/timeseries/eits",
            required_api_key_setting="census_api_key",
            default_identifiers=("mhs", "ressales", "marts"),
        ),
        build_official_api_config(
            catalog_by_id["fhfa-hpi"],
            connector_kind="fhfa_placeholder",
            endpoint_url=catalog_by_id["fhfa-hpi"].base_url,
        ),
        build_official_api_config(
            catalog_by_id["freddie-mac-pmms"],
            connector_kind="freddie_mac_placeholder",
            endpoint_url=catalog_by_id["freddie-mac-pmms"].base_url,
        ),
    ]


def build_official_api_config(
    source: SourceCatalogEntry,
    *,
    connector_kind: ConnectorKind,
    endpoint_url: str | None,
    required_api_key_setting: str | None = None,
    default_identifiers: tuple[str, ...] = (),
) -> OfficialAPIConfig:
    return OfficialAPIConfig(
        source_key=source.id,
        source_name=source.name,
        base_url=source.base_url,
        endpoint_url=endpoint_url,
        domains=tuple(source.domains),
        source_type=source.source_type,
        access_method=source.access_method,
        update_cadence=source.update_cadence,
        reliability_tier=source.reliability_tier,
        storage_policy=source.storage_policy,
        enabled=source.enabled_by_default,
        connector_kind=connector_kind,
        required_api_key_setting=required_api_key_setting,
        default_identifiers=default_identifiers,
    )


def ingest_configured_official_api_sources(session: Session) -> list[OfficialIngestionResult]:
    settings = get_settings()
    return [
        ingest_official_api_source(session, config, settings=settings)
        for config in get_configured_official_api_sources()
    ]


def ingest_official_api_source(
    session: Session,
    config: OfficialAPIConfig,
    *,
    settings: Settings | None = None,
) -> OfficialIngestionResult:
    settings = settings or get_settings()
    started_at = datetime.now(UTC)
    run = IngestionRun(
        source_key=config.source_key,
        run_type="manual",
        status="running",
        started_at=started_at,
        run_metadata={
            "connector_kind": config.connector_kind,
            "endpoint_url": config.endpoint_url,
            "identifiers": list(config.default_identifiers),
        },
    )
    session.add(run)
    session.flush()

    try:
        source = get_or_create_source(session, config)
        run.source = source

        missing_key = missing_required_api_key(config, settings)
        if missing_key:
            completed_at = datetime.now(UTC)
            run.status = "skipped"
            run.completed_at = completed_at
            run.error = missing_key
            update_source_health_skipped(session, source, config, started_at, missing_key)
            session.commit()
            return OfficialIngestionResult(
                source_key=config.source_key,
                status="skipped",
                items_seen=0,
                items_inserted=0,
                items_updated=0,
                items_skipped=0,
                error=missing_key,
            )

        if config.connector_kind == "sec_submissions":
            result = ingest_sec_submissions(session, source, config, settings)
        elif config.connector_kind == "fred_observations":
            result = ingest_fred_observations(session, source, config, settings)
        elif config.connector_kind == "census_eits":
            result = ingest_census_eits(session, source, config, settings)
        else:
            result = skip_placeholder_connector(session, source, config)

        completed_at = datetime.now(UTC)
        run.status = result.status
        run.completed_at = completed_at
        run.items_seen = result.items_seen
        run.items_inserted = result.items_inserted
        run.items_updated = result.items_updated
        run.items_skipped = result.items_skipped
        run.error = result.error

        if result.status == "success":
            update_source_health_success(session, source, config, started_at, completed_at)
        else:
            update_source_health_skipped(session, source, config, started_at, result.error or result.status)

        session.commit()
        return result
    except Exception as error:
        completed_at = datetime.now(UTC)
        message = str(error)
        run.status = "failed"
        run.completed_at = completed_at
        run.error = message
        source = session.scalar(select(Source).where(Source.name == config.source_name))
        update_source_health_failure(session, source, config, started_at, message)
        session.commit()
        return OfficialIngestionResult(
            source_key=config.source_key,
            status="failed",
            items_seen=0,
            items_inserted=0,
            items_updated=0,
            items_skipped=0,
            error=message,
        )


def ingest_sec_submissions(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    inserted = 0
    updated = 0
    records: list[SECSubmissionRecord] = []

    for cik in config.default_identifiers:
        payload = fetch_json(config.endpoint_url.format(identifier=cik), settings)
        records.extend(normalize_sec_submissions(config, payload, datetime.now(UTC)))

    for record in records:
        _, was_inserted = upsert_sec_submission(session, source, record)
        if was_inserted:
            inserted += 1
        else:
            updated += 1

    return OfficialIngestionResult(
        source_key=config.source_key,
        status="success",
        items_seen=len(records),
        items_inserted=inserted,
        items_updated=updated,
        items_skipped=0,
    )


def ingest_fred_observations(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    inserted = 0
    updated = 0
    skipped = 0
    records: list[StructuredObservationRecord] = []

    for series_id in config.default_identifiers:
        payload = fetch_json(build_fred_observations_url(config, series_id, settings), settings)
        records.extend(normalize_fred_observations(config, series_id, payload, datetime.now(UTC)))

    for record in records:
        observation, was_inserted = upsert_structured_observation(session, source, record)
        if observation is None:
            skipped += 1
        elif was_inserted:
            inserted += 1
        else:
            updated += 1

    return OfficialIngestionResult(
        source_key=config.source_key,
        status="success",
        items_seen=len(records),
        items_inserted=inserted,
        items_updated=updated,
        items_skipped=skipped,
    )


def ingest_census_eits(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    inserted = 0
    updated = 0
    skipped = 0
    records: list[StructuredObservationRecord] = []

    for dataset in config.default_identifiers:
        payload = fetch_json(build_census_eits_url(config, dataset, settings), settings)
        records.extend(normalize_census_eits_observations(config, dataset, payload, datetime.now(UTC)))

    for record in records:
        observation, was_inserted = upsert_structured_observation(session, source, record)
        if observation is None:
            skipped += 1
        elif was_inserted:
            inserted += 1
        else:
            updated += 1

    return OfficialIngestionResult(
        source_key=config.source_key,
        status="success",
        items_seen=len(records),
        items_inserted=inserted,
        items_updated=updated,
        items_skipped=skipped,
    )


def skip_placeholder_connector(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
) -> OfficialIngestionResult:
    session.flush()
    return OfficialIngestionResult(
        source_key=config.source_key,
        status="skipped",
        items_seen=0,
        items_inserted=0,
        items_updated=0,
        items_skipped=0,
        error=f"{config.connector_kind} connector scaffolded; parser will be implemented in a later pass.",
    )


def normalize_sec_submissions(
    config: OfficialAPIConfig,
    payload: dict[str, Any],
    retrieved_at: datetime,
    *,
    limit: int = 20,
) -> list[SECSubmissionRecord]:
    cik = str(payload["cik"]).zfill(10)
    company_name = str(payload.get("name") or f"CIK {cik}")
    recent = payload.get("filings", {}).get("recent", {})
    accession_numbers = recent.get("accessionNumber", [])
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    primary_documents = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    records: list[SECSubmissionRecord] = []
    for index, accession_number in enumerate(accession_numbers[:limit]):
        primary_document = value_at(primary_documents, index)
        url = build_sec_filing_url(cik, accession_number, primary_document)
        records.append(
            SECSubmissionRecord(
                source_key=config.source_key,
                cik=cik,
                company_name=company_name,
                accession_number=accession_number,
                form=value_at(forms, index) or "FILING",
                filing_date=value_at(filing_dates, index),
                report_date=value_at(report_dates, index),
                primary_document=primary_document,
                description=value_at(descriptions, index),
                url=url,
                retrieved_at=retrieved_at,
                domains=list(config.domains),
                storage_policy=config.storage_policy,
            )
        )

    return records


def normalize_fred_observations(
    config: OfficialAPIConfig,
    series_id: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    observations: list[StructuredObservationRecord] = []

    for item in payload.get("observations", []):
        raw_value = item.get("value")
        if raw_value in (None, "."):
            continue

        observations.append(
            StructuredObservationRecord(
                source_key=config.source_key,
                series_id=series_id,
                series_name=series_id,
                value=float(raw_value),
                unit=None,
                period=item["date"],
                released_at=parse_iso_date(item.get("date")),
                retrieved_at=retrieved_at,
                vintage=item.get("realtime_end"),
                external_id=f"{series_id}:{item['date']}:{item.get('realtime_end', '')}",
            )
        )

    return observations


def normalize_census_eits_observations(
    config: OfficialAPIConfig,
    dataset: str,
    payload: list[list[Any]],
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    if not payload:
        return []

    header = [str(column) for column in payload[0]]
    required_columns = {"cell_value", "time"}
    missing_columns = required_columns - set(header)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Census EITS response missing required columns: {missing}")

    observations: list[StructuredObservationRecord] = []
    for row in payload[1:]:
        values = row_to_dict(header, row)
        raw_value = values.get("cell_value")
        if raw_value in (None, "", "NA", "N/A", "(X)"):
            continue

        value = parse_float(raw_value)
        if value is None:
            continue

        period = required_text(values.get("time"), "Census EITS period")
        data_type_code = values.get("data_type_code") or "value"
        category_code = values.get("category_code") or "all"
        seasonally_adjusted = values.get("seasonally_adj") or "unknown"
        time_slot_id = values.get("time_slot_id") or "none"
        region = normalize_census_region(values)
        series_id = build_census_series_id(dataset, data_type_code, category_code, seasonally_adjusted, time_slot_id)

        observations.append(
            StructuredObservationRecord(
                source_key=config.source_key,
                series_id=series_id,
                series_name=build_census_series_name(dataset, data_type_code, category_code, seasonally_adjusted),
                value=value,
                unit=None,
                period=period,
                released_at=parse_census_period(period),
                retrieved_at=retrieved_at,
                vintage=values.get("error_data"),
                region=region,
                external_id=f"{series_id}:{period}:{region or 'all'}",
            )
        )

    return observations


def upsert_sec_submission(
    session: Session,
    source: Source,
    record: SECSubmissionRecord,
) -> tuple[Article, bool]:
    existing_external_id = session.scalar(
        select(ExternalID).where(
            ExternalID.source_key == record.source_key,
            ExternalID.external_id == record.accession_number,
            ExternalID.entity_type == "sec_submission",
        )
    )

    if existing_external_id and existing_external_id.article:
        article = existing_external_id.article
        article.retrieved_at = record.retrieved_at
        article.summary = record.description or article.summary
        article.content_hash = record.content_hash
        return article, False

    article = session.scalar(select(Article).where(Article.url == record.url))
    was_inserted = article is None

    if article is None:
        article = Article(
            source=source,
            title=record.title,
            url=record.url,
            canonical_url=record.url,
            publisher=source.name,
            published_at=parse_iso_date(record.filing_date),
            retrieved_at=record.retrieved_at,
            summary=record.description,
            excerpt=record.description,
            domains=record.domains,
            companies=[record.company_name],
            content_hash=record.content_hash,
            dedupe_group_id=record.accession_number,
            storage_policy=record.storage_policy,
        )
        session.add(article)
        session.flush()
    else:
        article.retrieved_at = record.retrieved_at
        article.summary = record.description or article.summary
        article.content_hash = record.content_hash

    ensure_external_id(
        session,
        source_key=record.source_key,
        external_id=record.accession_number,
        entity_type="sec_submission",
        article=article,
        metadata={"cik": record.cik, "form": record.form, "filing_date": record.filing_date},
    )
    return article, was_inserted


def upsert_structured_observation(
    session: Session,
    source: Source,
    record: StructuredObservationRecord,
) -> tuple[EconomicObservation | None, bool]:
    observation = session.scalar(
        select(EconomicObservation).where(
            EconomicObservation.series_id == record.series_id,
            EconomicObservation.period == record.period,
            EconomicObservation.vintage == record.vintage,
            EconomicObservation.region == record.region,
        )
    )
    was_inserted = observation is None

    if observation is None:
        observation = EconomicObservation(
            source=source,
            series_id=record.series_id,
            series_name=record.series_name,
            value=record.value,
            unit=record.unit,
            period=record.period,
            released_at=record.released_at,
            retrieved_at=record.retrieved_at,
            vintage=record.vintage,
            region=record.region,
        )
        session.add(observation)
        session.flush()
    else:
        observation.value = record.value
        observation.retrieved_at = record.retrieved_at

    if record.external_id:
        ensure_external_id(
            session,
            source_key=record.source_key,
            external_id=record.external_id,
            entity_type="economic_observation",
            observation=observation,
            metadata={"series_id": record.series_id, "period": record.period},
        )

    return observation, was_inserted


def ensure_external_id(
    session: Session,
    *,
    source_key: str,
    external_id: str,
    entity_type: str,
    article: Article | None = None,
    observation: EconomicObservation | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    existing = session.scalar(
        select(ExternalID).where(
            ExternalID.source_key == source_key,
            ExternalID.external_id == external_id,
            ExternalID.entity_type == entity_type,
        )
    )

    if existing:
        existing.article = article or existing.article
        existing.observation = observation or existing.observation
        return

    session.add(
        ExternalID(
            source_key=source_key,
            external_id=external_id,
            entity_type=entity_type,
            article=article,
            observation=observation,
            id_metadata=metadata or {},
        )
    )


def get_or_create_source(session: Session, config: OfficialAPIConfig) -> Source:
    source = session.scalar(select(Source).where(Source.name == config.source_name))
    if source:
        return source

    source = Source(
        name=config.source_name,
        base_url=config.base_url,
        source_type=config.source_type,
        domains=list(config.domains),
        access_method=config.access_method,
        update_cadence=config.update_cadence,
        reliability_tier=config.reliability_tier,
        enabled=config.enabled,
    )
    session.add(source)
    session.flush()
    return source


def missing_required_api_key(config: OfficialAPIConfig, settings: Settings) -> str | None:
    if config.required_api_key_setting is None:
        return None

    if getattr(settings, config.required_api_key_setting):
        return None

    return f"Missing required API key setting: {config.required_api_key_setting.upper()}"


def fetch_json(url: str, settings: Settings) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": settings.investoragent_user_agent,
            "Accept": "application/json",
        },
    )
    context = ssl.create_default_context(cafile=certifi.where())

    with urlopen(request, timeout=20, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def build_fred_observations_url(
    config: OfficialAPIConfig,
    series_id: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "series_id": series_id,
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": "12",
        }
    )
    return f"{config.endpoint_url}?{query}"


def build_census_eits_url(
    config: OfficialAPIConfig,
    dataset: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "get": "data_type_code,time_slot_id,seasonally_adj,category_code,cell_value,error_data",
            "for": "us:*",
            "time": "from 2024",
            "key": settings.census_api_key,
        }
    )
    return f"{config.endpoint_url}/{dataset}?{query}"


def row_to_dict(header: list[str], row: list[Any]) -> dict[str, str | None]:
    return {
        column: None if index >= len(row) or row[index] is None else str(row[index])
        for index, column in enumerate(header)
    }


def parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def normalize_census_region(values: dict[str, str | None]) -> str | None:
    if values.get("us"):
        return "US"
    return None


def build_census_series_id(
    dataset: str,
    data_type_code: str | None,
    category_code: str | None,
    seasonally_adjusted: str | None,
    time_slot_id: str | None,
) -> str:
    parts = [
        "CENSUS_EITS",
        dataset.upper(),
        normalize_series_part(data_type_code),
        normalize_series_part(category_code),
        normalize_series_part(seasonally_adjusted),
        normalize_series_part(time_slot_id),
    ]
    return ":".join(parts)


def build_census_series_name(
    dataset: str,
    data_type_code: str | None,
    category_code: str | None,
    seasonally_adjusted: str | None,
) -> str:
    dataset_name = {
        "mhs": "New Residential Construction",
        "ressales": "New Residential Sales",
        "marts": "Monthly Retail Trade",
    }.get(dataset, dataset.upper())
    adjustment = "seasonally adjusted" if seasonally_adjusted == "yes" else "not seasonally adjusted"
    return f"{dataset_name} - {data_type_code or 'value'} - {category_code or 'all categories'} ({adjustment})"


def normalize_series_part(value: str | None) -> str:
    if not value:
        return "ALL"
    return value.strip().upper().replace(" ", "_").replace(":", "_")


def parse_census_period(value: str) -> datetime | None:
    if len(value) == 4 and value.isdigit():
        return datetime(int(value), 1, 1, tzinfo=UTC)
    if len(value) == 7 and value[4] == "-":
        year, month = value.split("-")
        return datetime(int(year), int(month), 1, tzinfo=UTC)
    return parse_iso_date(value)


def build_sec_filing_url(cik: str, accession_number: str, primary_document: str | None) -> str:
    accession_path = accession_number.replace("-", "")
    cik_path = str(int(cik))
    if primary_document:
        return f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accession_path}/{primary_document}"
    return f"https://www.sec.gov/Archives/edgar/data/{cik_path}/{accession_path}"


def update_source_health_success(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    attempted_at: datetime,
    completed_at: datetime,
) -> None:
    health = get_or_create_source_health(session, config)
    health.source = source
    health.status = "fresh"
    health.last_attempt_at = attempted_at
    health.last_success_at = completed_at
    health.consecutive_failures = 0
    health.last_error = None
    health.stale_after = completed_at + timedelta(hours=health.freshness_window_hours)


def update_source_health_skipped(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    attempted_at: datetime,
    reason: str,
) -> None:
    health = get_or_create_source_health(session, config)
    health.source = source
    health.status = "skipped"
    health.last_attempt_at = attempted_at
    health.last_error = reason


def update_source_health_failure(
    session: Session,
    source: Source | None,
    config: OfficialAPIConfig,
    attempted_at: datetime,
    error: str,
) -> None:
    health = get_or_create_source_health(session, config)
    health.source = source
    health.status = "failed"
    health.last_attempt_at = attempted_at
    health.consecutive_failures += 1
    health.last_error = error


def get_or_create_source_health(session: Session, config: OfficialAPIConfig) -> SourceHealth:
    health = session.scalar(select(SourceHealth).where(SourceHealth.source_key == config.source_key))
    if health:
        return health

    health = SourceHealth(
        source_key=config.source_key,
        status="not_configured",
        freshness_window_hours=freshness_window_for_cadence(config.update_cadence),
        health_metadata={"connector_kind": config.connector_kind, "endpoint_url": config.endpoint_url},
    )
    session.add(health)
    session.flush()
    return health


def freshness_window_for_cadence(update_cadence: str) -> int:
    if "intraday" in update_cadence:
        return 6
    if "weekly" in update_cadence:
        return 168
    if "monthly" in update_cadence or "quarterly" in update_cadence:
        return 720
    return 24


def parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=UTC)


def value_at(values: list[Any], index: int) -> Any | None:
    if index >= len(values):
        return None
    return values[index]


def required_text(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"Missing required field: {field_name}")
    return value.strip()
