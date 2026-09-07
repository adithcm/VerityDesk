import csv
import json
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from zipfile import ZipFile

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
    "fhfa_hpi",
    "freddie_mac_pmms",
    "alpha_vantage_news_sentiment",
    "finnhub_company_news",
    "newsapi_everything",
    "gdelt_doc",
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
class ProviderArticleRecord:
    source_key: str
    title: str
    url: str
    publisher: str | None
    published_at: datetime | None
    retrieved_at: datetime
    summary: str | None
    excerpt: str | None
    domains: list[str]
    companies: list[str]
    storage_policy: str
    external_id: str
    metadata: dict[str, Any]

    @property
    def content_hash(self) -> str:
        raw = "|".join(
            [
                self.source_key,
                self.external_id,
                self.title,
                self.url,
                self.published_at.isoformat() if self.published_at else "",
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


FHFA_HPI_DOWNLOAD_URLS = {
    "state": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.txt",
    "us_census": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_us_and_census.txt",
    "metro": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.txt",
}


US_STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


FHFA_US_CENSUS_REGION_NAMES = {
    "USA": "United States",
    "DV_ENC": "East North Central",
    "DV_ESC": "East South Central",
    "DV_MA": "Middle Atlantic",
    "DV_MT": "Mountain",
    "DV_MTN": "Mountain",
    "DV_NE": "New England",
    "DV_PA": "Pacific",
    "DV_SA": "South Atlantic",
    "DV_WNC": "West North Central",
    "DV_WSC": "West South Central",
}


FREDDIE_MAC_PMMS_WORKBOOK_URL = "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx"
ALPHA_VANTAGE_QUERY_URL = "https://www.alphavantage.co/query"
FINNHUB_API_URL = "https://finnhub.io/api/v1"
NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
OPTIONAL_MARKET_SYMBOLS = ("AAPL", "MSFT", "NVDA", "TSLA")


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
            connector_kind="fhfa_hpi",
            endpoint_url="https://www.fhfa.gov/hpi/download/quarterly_datasets",
            default_identifiers=("us_census", "state", "metro"),
        ),
        build_official_api_config(
            catalog_by_id["freddie-mac-pmms"],
            connector_kind="freddie_mac_pmms",
            endpoint_url=FREDDIE_MAC_PMMS_WORKBOOK_URL,
            default_identifiers=("30_year_fixed", "15_year_fixed"),
        ),
        build_official_api_config(
            catalog_by_id["alpha-vantage"],
            connector_kind="alpha_vantage_news_sentiment",
            endpoint_url=ALPHA_VANTAGE_QUERY_URL,
            required_api_key_setting="alpha_vantage_api_key",
            default_identifiers=(
                "financial_markets",
                "economy_macro",
                "real_estate",
                "technology",
                "energy_transportation",
            ),
        ),
        build_official_api_config(
            catalog_by_id["finnhub"],
            connector_kind="finnhub_company_news",
            endpoint_url=FINNHUB_API_URL,
            required_api_key_setting="finnhub_api_key",
            default_identifiers=("AAPL", "MSFT", "NVDA", "TSLA"),
        ),
        build_official_api_config(
            catalog_by_id["newsapi"],
            connector_kind="newsapi_everything",
            endpoint_url=NEWSAPI_EVERYTHING_URL,
            required_api_key_setting="newsapi_key",
            default_identifiers=("markets OR economy", "housing market", "artificial intelligence"),
        ),
        build_official_api_config(
            catalog_by_id["gdelt-cloud"],
            connector_kind="gdelt_doc",
            endpoint_url=GDELT_DOC_URL,
            default_identifiers=("global markets", "geopolitics energy", "housing economy"),
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
        elif config.connector_kind == "fhfa_hpi":
            result = ingest_fhfa_hpi(session, source, config, settings)
        elif config.connector_kind == "freddie_mac_pmms":
            result = ingest_freddie_mac_pmms(session, source, config, settings)
        elif config.connector_kind == "alpha_vantage_news_sentiment":
            result = ingest_alpha_vantage_news_sentiment(session, source, config, settings)
        elif config.connector_kind == "finnhub_company_news":
            result = ingest_finnhub_company_news(session, source, config, settings)
        elif config.connector_kind == "newsapi_everything":
            result = ingest_newsapi_everything(session, source, config, settings)
        elif config.connector_kind == "gdelt_doc":
            result = ingest_gdelt_doc(session, source, config, settings)
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


def ingest_fhfa_hpi(
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
        payload = fetch_text(build_fhfa_hpi_url(dataset), settings)
        records.extend(normalize_fhfa_hpi_observations(config, dataset, payload, datetime.now(UTC)))

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


def ingest_freddie_mac_pmms(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    inserted = 0
    updated = 0
    skipped = 0
    payload = fetch_bytes(required_text(config.endpoint_url, "Freddie Mac PMMS endpoint URL"), settings)
    records = normalize_freddie_mac_pmms_observations(config, payload, datetime.now(UTC))

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


def ingest_alpha_vantage_news_sentiment(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    records: list[ProviderArticleRecord] = []
    observations: list[StructuredObservationRecord] = []
    for topic in config.default_identifiers:
        payload = fetch_json(build_alpha_vantage_news_sentiment_url(config, topic, settings), settings)
        records.extend(normalize_alpha_vantage_news_sentiment(config, topic, payload, datetime.now(UTC)))

    top_movers_payload = fetch_json(build_alpha_vantage_top_gainers_losers_url(config, settings), settings)
    observations.extend(normalize_alpha_vantage_top_gainers_losers(config, top_movers_payload, datetime.now(UTC)))

    for symbol in OPTIONAL_MARKET_SYMBOLS:
        quote_payload = fetch_json(build_alpha_vantage_global_quote_url(config, symbol, settings), settings)
        observations.extend(normalize_alpha_vantage_global_quote(config, symbol, quote_payload, datetime.now(UTC)))

    article_result = upsert_provider_articles(session, source, config, records)
    observation_result = upsert_structured_observations(session, source, config, observations)
    return combine_ingestion_results(config.source_key, article_result, observation_result)


def ingest_finnhub_company_news(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    records: list[ProviderArticleRecord] = []
    observations: list[StructuredObservationRecord] = []
    for symbol in config.default_identifiers:
        payload = fetch_json(build_finnhub_company_news_url(config, symbol, settings), settings)
        records.extend(normalize_finnhub_company_news(config, symbol, payload, datetime.now(UTC)))
        quote_payload = fetch_json(build_finnhub_quote_url(config, symbol, settings), settings)
        observations.extend(normalize_finnhub_quote(config, symbol, quote_payload, datetime.now(UTC)))

    article_result = upsert_provider_articles(session, source, config, records)
    observation_result = upsert_structured_observations(session, source, config, observations)
    return combine_ingestion_results(config.source_key, article_result, observation_result)


def ingest_newsapi_everything(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    records: list[ProviderArticleRecord] = []
    for query in config.default_identifiers:
        payload = fetch_json(build_newsapi_everything_url(config, query, settings), settings)
        records.extend(normalize_newsapi_everything(config, query, payload, datetime.now(UTC)))

    for category in ("business", "technology", "general"):
        payload = fetch_json(build_newsapi_top_headlines_url(config, category, settings), settings)
        records.extend(normalize_newsapi_everything(config, f"top-headlines:{category}", payload, datetime.now(UTC)))
    return upsert_provider_articles(session, source, config, records)


def ingest_gdelt_doc(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    settings: Settings,
) -> OfficialIngestionResult:
    records: list[ProviderArticleRecord] = []
    for index, query in enumerate(config.default_identifiers):
        if index:
            time.sleep(5)
        payload = fetch_json(build_gdelt_doc_url(config, query), settings)
        records.extend(normalize_gdelt_doc(config, query, payload, datetime.now(UTC)))
    return upsert_provider_articles(session, source, config, records)


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


def normalize_fhfa_hpi_observations(
    config: OfficialAPIConfig,
    dataset: str,
    payload: str,
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    if not payload.strip():
        return []

    observations: list[StructuredObservationRecord] = []
    reader = csv.reader(payload.splitlines(), delimiter="\t")
    for row_number, row in enumerate(reader, start=1):
        if not row or all(not value.strip() for value in row):
            continue

        observations.extend(normalize_fhfa_hpi_row(config, dataset, row, row_number, retrieved_at))

    return observations


def normalize_fhfa_hpi_row(
    config: OfficialAPIConfig,
    dataset: str,
    row: list[str],
    row_number: int,
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    if dataset == "state":
        if len(row) < 4:
            raise ValueError(f"FHFA state row {row_number} missing required columns")
        region_code = row[0].strip().upper()
        year = required_text(row[1], "FHFA state year")
        quarter = required_text(row[2], "FHFA state quarter")
        raw_value = row[3].strip()
        value = parse_float(raw_value)
        if value is None:
            return []
        region = US_STATE_NAMES.get(region_code, region_code)
        series_id = f"FHFA_HPI:STATE:{region_code}"
        period = build_quarter_period(year, quarter)
        return [
            StructuredObservationRecord(
                source_key=config.source_key,
                series_id=series_id,
                series_name=f"FHFA All-Transactions HPI - {region}",
                value=value,
                unit="index",
                period=period,
                released_at=parse_quarter_period(year, quarter),
                retrieved_at=retrieved_at,
                region=region,
                external_id=f"{series_id}:{period}",
            )
        ]

    if dataset == "us_census":
        if len(row) < 4:
            raise ValueError(f"FHFA U.S./Census row {row_number} missing required columns")
        region_code = row[0].strip().upper()
        year = required_text(row[1], "FHFA U.S./Census year")
        quarter = required_text(row[2], "FHFA U.S./Census quarter")
        value = parse_float(row[3].strip())
        if value is None:
            return []
        region = FHFA_US_CENSUS_REGION_NAMES.get(region_code, region_code)
        series_id = f"FHFA_HPI:US_CENSUS:{region_code}"
        period = build_quarter_period(year, quarter)
        return [
            StructuredObservationRecord(
                source_key=config.source_key,
                series_id=series_id,
                series_name=f"FHFA All-Transactions HPI - {region}",
                value=value,
                unit="index",
                period=period,
                released_at=parse_quarter_period(year, quarter),
                retrieved_at=retrieved_at,
                region=region,
                external_id=f"{series_id}:{period}",
            )
        ]

    if dataset == "metro":
        if len(row) < 5:
            raise ValueError(f"FHFA metro row {row_number} missing required columns")
        metro_name = required_text(row[0], "FHFA metro name")
        cbsa_code = required_text(row[1], "FHFA metro CBSA code")
        year = required_text(row[2], "FHFA metro year")
        quarter = required_text(row[3], "FHFA metro quarter")
        value = parse_float(row[4].strip())
        if value is None:
            return []
        series_id = f"FHFA_HPI:METRO:{cbsa_code}"
        period = build_quarter_period(year, quarter)
        return [
            StructuredObservationRecord(
                source_key=config.source_key,
                series_id=series_id,
                series_name=f"FHFA All-Transactions HPI - {metro_name}",
                value=value,
                unit="index",
                period=period,
                released_at=parse_quarter_period(year, quarter),
                retrieved_at=retrieved_at,
                region=metro_name,
                external_id=f"{series_id}:{period}",
            )
        ]

    raise ValueError(f"Unsupported FHFA HPI dataset: {dataset}")


def normalize_freddie_mac_pmms_observations(
    config: OfficialAPIConfig,
    workbook: bytes,
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    rows = parse_xlsx_rows(workbook)
    if not rows:
        return []

    header_index = find_pmms_header_row(rows)
    if header_index is None:
        raise ValueError("Freddie Mac PMMS workbook missing date and mortgage rate columns")

    header = rows[header_index]
    date_index = find_pmms_date_column(header)
    thirty_year_index = find_pmms_rate_column(header, "30")
    fifteen_year_index = find_pmms_rate_column(header, "15")
    if date_index is None or (thirty_year_index is None and fifteen_year_index is None):
        raise ValueError("Freddie Mac PMMS workbook missing supported mortgage rate columns")

    observations: list[StructuredObservationRecord] = []
    series_columns = [
        (
            thirty_year_index,
            "FREDDIE_PMMS:30Y_FIXED",
            "Freddie Mac PMMS - 30-Year Fixed-Rate Mortgage",
        ),
        (
            fifteen_year_index,
            "FREDDIE_PMMS:15Y_FIXED",
            "Freddie Mac PMMS - 15-Year Fixed-Rate Mortgage",
        ),
    ]

    for row in rows[header_index + 1 :]:
        period_date = parse_pmms_date(value_at(row, date_index))
        if period_date is None:
            continue

        for column_index, series_id, series_name in series_columns:
            if column_index is None:
                continue
            raw_value = value_at(row, column_index)
            value = parse_float(str(raw_value).replace("%", "")) if raw_value is not None else None
            if value is None:
                continue

            period = period_date.date().isoformat()
            observations.append(
                StructuredObservationRecord(
                    source_key=config.source_key,
                    series_id=series_id,
                    series_name=series_name,
                    value=value,
                    unit="percent",
                    period=period,
                    released_at=period_date,
                    retrieved_at=retrieved_at,
                    region="United States",
                    external_id=f"{series_id}:{period}",
                )
            )

    return observations


def normalize_alpha_vantage_news_sentiment(
    config: OfficialAPIConfig,
    topic: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[ProviderArticleRecord]:
    if "Error Message" in payload:
        raise ValueError(f"Alpha Vantage error: {payload['Error Message']}")
    if "Note" in payload:
        raise ValueError(f"Alpha Vantage limit notice: {payload['Note']}")

    feed = payload.get("feed")
    if feed is None:
        return []
    if not isinstance(feed, list):
        raise ValueError("Alpha Vantage response has malformed feed")

    records: list[ProviderArticleRecord] = []
    for item in feed:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            continue
        related = [
            str(ticker.get("ticker"))
            for ticker in item.get("ticker_sentiment", [])
            if isinstance(ticker, dict) and ticker.get("ticker")
        ]
        published_at = parse_alpha_vantage_time(item.get("time_published"))
        records.append(
            ProviderArticleRecord(
                source_key=config.source_key,
                title=str(title),
                url=str(url),
                publisher=optional_text(item.get("source")),
                published_at=published_at,
                retrieved_at=retrieved_at,
                summary=optional_text(item.get("summary")),
                excerpt=optional_text(item.get("summary")),
                domains=list(config.domains),
                companies=related,
                storage_policy=config.storage_policy,
                external_id=f"alpha-vantage:{stable_external_part(str(url))}",
                metadata={
                    "topic": topic,
                    "overall_sentiment_score": item.get("overall_sentiment_score"),
                    "overall_sentiment_label": item.get("overall_sentiment_label"),
                    "source_domain": item.get("source_domain"),
                },
            )
        )
    return records


def normalize_alpha_vantage_top_gainers_losers(
    config: OfficialAPIConfig,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    if "Error Message" in payload:
        raise ValueError(f"Alpha Vantage error: {payload['Error Message']}")
    if "Note" in payload:
        raise ValueError(f"Alpha Vantage limit notice: {payload['Note']}")

    observations: list[StructuredObservationRecord] = []
    period = retrieved_at.date().isoformat()
    groups = (
        ("top_gainers", "Top Gainer"),
        ("top_losers", "Top Loser"),
        ("most_actively_traded", "Most Active"),
    )
    for group_key, group_name in groups:
        group_items = payload.get(group_key, [])
        if not isinstance(group_items, list):
            raise ValueError(f"Alpha Vantage response has malformed {group_key}")
        for item in group_items[:10]:
            if not isinstance(item, dict):
                continue
            ticker = optional_text(item.get("ticker"))
            change_percent = parse_percentage(item.get("change_percentage"))
            if ticker is None or change_percent is None:
                continue
            normalized_ticker = normalize_series_part(ticker)
            observations.append(
                StructuredObservationRecord(
                    source_key=config.source_key,
                    series_id=f"ALPHA_VANTAGE:{group_key.upper()}:{normalized_ticker}:CHANGE_PERCENT",
                    series_name=f"Alpha Vantage {group_name} - {ticker} Change Percent",
                    value=change_percent,
                    unit="percent",
                    period=period,
                    released_at=parse_iso_date(period),
                    retrieved_at=retrieved_at,
                    region="US Market",
                    external_id=f"ALPHA_VANTAGE:{group_key}:{normalized_ticker}:{period}",
                )
            )
    return observations


def normalize_alpha_vantage_global_quote(
    config: OfficialAPIConfig,
    symbol: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    if "Error Message" in payload:
        raise ValueError(f"Alpha Vantage error: {payload['Error Message']}")
    if "Note" in payload:
        raise ValueError(f"Alpha Vantage limit notice: {payload['Note']}")

    quote = payload.get("Global Quote")
    if quote is None:
        return []
    if not isinstance(quote, dict):
        raise ValueError("Alpha Vantage response has malformed Global Quote")

    return build_quote_observations(
        config,
        provider_prefix="ALPHA_VANTAGE",
        symbol=symbol,
        price=parse_float(str(quote.get("05. price") or "")),
        change=parse_float(str(quote.get("09. change") or "")),
        change_percent=parse_percentage(quote.get("10. change percent")),
        volume=parse_float(str(quote.get("06. volume") or "")),
        period=optional_text(quote.get("07. latest trading day")) or retrieved_at.date().isoformat(),
        retrieved_at=retrieved_at,
    )


def normalize_finnhub_company_news(
    config: OfficialAPIConfig,
    symbol: str,
    payload: Any,
    retrieved_at: datetime,
) -> list[ProviderArticleRecord]:
    if not isinstance(payload, list):
        raise ValueError("Finnhub company news response must be a list")

    records: list[ProviderArticleRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        headline = item.get("headline")
        if not url or not headline:
            continue
        news_id = str(item.get("id") or stable_external_part(str(url)))
        records.append(
            ProviderArticleRecord(
                source_key=config.source_key,
                title=str(headline),
                url=str(url),
                publisher=optional_text(item.get("source")),
                published_at=parse_unix_timestamp(item.get("datetime")),
                retrieved_at=retrieved_at,
                summary=optional_text(item.get("summary")),
                excerpt=optional_text(item.get("summary")),
                domains=list(config.domains),
                companies=[symbol],
                storage_policy=config.storage_policy,
                external_id=f"finnhub:{news_id}",
                metadata={"symbol": symbol, "category": item.get("category"), "related": item.get("related")},
            )
        )
    return records


def normalize_finnhub_quote(
    config: OfficialAPIConfig,
    symbol: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[StructuredObservationRecord]:
    if not isinstance(payload, dict):
        raise ValueError("Finnhub quote response must be an object")

    timestamp = parse_unix_timestamp(payload.get("t"))
    period = timestamp.date().isoformat() if timestamp else retrieved_at.date().isoformat()
    return build_quote_observations(
        config,
        provider_prefix="FINNHUB",
        symbol=symbol,
        price=parse_float(str(payload.get("c") or "")),
        change=parse_float(str(payload.get("d") or "")),
        change_percent=parse_float(str(payload.get("dp") or "")),
        volume=None,
        period=period,
        retrieved_at=retrieved_at,
        released_at=timestamp,
    )


def normalize_newsapi_everything(
    config: OfficialAPIConfig,
    query: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[ProviderArticleRecord]:
    if payload.get("status") == "error":
        raise ValueError(f"NewsAPI error: {payload.get('message') or payload.get('code')}")

    articles = payload.get("articles")
    if articles is None:
        return []
    if not isinstance(articles, list):
        raise ValueError("NewsAPI response has malformed articles")

    records: list[ProviderArticleRecord] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            continue
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        records.append(
            ProviderArticleRecord(
                source_key=config.source_key,
                title=str(title),
                url=str(url),
                publisher=optional_text(source.get("name")),
                published_at=parse_iso_date(item.get("publishedAt")),
                retrieved_at=retrieved_at,
                summary=optional_text(item.get("description")),
                excerpt=optional_text(item.get("content")) or optional_text(item.get("description")),
                domains=list(config.domains),
                companies=[],
                storage_policy=config.storage_policy,
                external_id=f"newsapi:{stable_external_part(f'{query}:{url}')}",
                metadata={"query": query, "source_id": source.get("id"), "author": item.get("author")},
            )
        )
    return records


def normalize_gdelt_doc(
    config: OfficialAPIConfig,
    query: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[ProviderArticleRecord]:
    articles = payload.get("articles")
    if articles is None:
        return []
    if not isinstance(articles, list):
        raise ValueError("GDELT DOC response has malformed articles")

    records: list[ProviderArticleRecord] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            continue
        records.append(
            ProviderArticleRecord(
                source_key=config.source_key,
                title=str(title),
                url=str(url),
                publisher=optional_text(item.get("sourcecountry")) or optional_text(item.get("domain")),
                published_at=parse_gdelt_seendate(item.get("seendate")),
                retrieved_at=retrieved_at,
                summary=None,
                excerpt=None,
                domains=list(config.domains),
                companies=[],
                storage_policy=config.storage_policy,
                external_id=f"gdelt:{stable_external_part(f'{query}:{url}')}",
                metadata={
                    "query": query,
                    "domain": item.get("domain"),
                    "language": item.get("language"),
                    "source_country": item.get("sourcecountry"),
                },
            )
        )
    return records


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


def upsert_provider_articles(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    records: list[ProviderArticleRecord],
) -> OfficialIngestionResult:
    inserted = 0
    updated = 0
    skipped = 0

    for record in records:
        article, was_inserted = upsert_provider_article(session, source, record)
        if article is None:
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


def upsert_structured_observations(
    session: Session,
    source: Source,
    config: OfficialAPIConfig,
    records: list[StructuredObservationRecord],
) -> OfficialIngestionResult:
    inserted = 0
    updated = 0
    skipped = 0

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


def combine_ingestion_results(source_key: str, *results: OfficialIngestionResult) -> OfficialIngestionResult:
    errors = [result.error for result in results if result.error]
    return OfficialIngestionResult(
        source_key=source_key,
        status="success",
        items_seen=sum(result.items_seen for result in results),
        items_inserted=sum(result.items_inserted for result in results),
        items_updated=sum(result.items_updated for result in results),
        items_skipped=sum(result.items_skipped for result in results),
        error="; ".join(errors) if errors else None,
    )


def upsert_provider_article(
    session: Session,
    source: Source,
    record: ProviderArticleRecord,
) -> tuple[Article | None, bool]:
    existing_external_id = session.scalar(
        select(ExternalID).where(
            ExternalID.source_key == record.source_key,
            ExternalID.external_id == record.external_id,
            ExternalID.entity_type == "provider_article",
        )
    )

    if existing_external_id and existing_external_id.article:
        article = existing_external_id.article
        article.retrieved_at = record.retrieved_at
        article.summary = record.summary or article.summary
        article.excerpt = record.excerpt or article.excerpt
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
            publisher=record.publisher or source.name,
            published_at=record.published_at,
            retrieved_at=record.retrieved_at,
            summary=record.summary,
            excerpt=record.excerpt,
            domains=record.domains,
            companies=record.companies,
            content_hash=record.content_hash,
            dedupe_group_id=record.external_id,
            storage_policy=record.storage_policy,
        )
        session.add(article)
        session.flush()
    else:
        article.retrieved_at = record.retrieved_at
        article.summary = record.summary or article.summary
        article.excerpt = record.excerpt or article.excerpt
        article.content_hash = record.content_hash

    ensure_external_id(
        session,
        source_key=record.source_key,
        external_id=record.external_id,
        entity_type="provider_article",
        article=article,
        metadata=record.metadata,
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


def fetch_json(url: str, settings: Settings) -> Any:
    request = Request(
        url,
        headers=build_json_request_headers(url, settings),
    )
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with urlopen(request, timeout=20, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")[:500]
        raise ValueError(f"HTTP {error.code} from {url_without_secret(url)}: {message}") from error


def fetch_text(url: str, settings: Settings) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": settings.investoragent_user_agent,
            "Accept": "text/plain,text/csv,*/*",
        },
    )
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with urlopen(request, timeout=30, context=context) as response:
            return response.read().decode("utf-8-sig")
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")[:500]
        raise ValueError(f"HTTP {error.code} from {url_without_secret(url)}: {message}") from error


def fetch_bytes(url: str, settings: Settings) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": settings.investoragent_user_agent,
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
        },
    )
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with urlopen(request, timeout=30, context=context) as response:
            return response.read()
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")[:500]
        raise ValueError(f"HTTP {error.code} from {url_without_secret(url)}: {message}") from error


def build_json_request_headers(url: str, settings: Settings) -> dict[str, str]:
    headers = {
        "User-Agent": settings.investoragent_user_agent,
        "Accept": "application/json",
    }
    if urlsplit(url).netloc == "newsapi.org" and settings.newsapi_key:
        headers["User-Agent"] = "InvestorAgent/0.1"
        headers["X-Api-Key"] = settings.newsapi_key
    return headers


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


def build_fhfa_hpi_url(dataset: str) -> str:
    try:
        return FHFA_HPI_DOWNLOAD_URLS[dataset]
    except KeyError as error:
        raise ValueError(f"Unsupported FHFA HPI dataset: {dataset}") from error


def build_alpha_vantage_news_sentiment_url(
    config: OfficialAPIConfig,
    topic: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "function": "NEWS_SENTIMENT",
            "topics": topic,
            "sort": "LATEST",
            "limit": "25",
            "apikey": settings.alpha_vantage_api_key,
        }
    )
    return f"{config.endpoint_url}?{query}"


def build_alpha_vantage_top_gainers_losers_url(
    config: OfficialAPIConfig,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "function": "TOP_GAINERS_LOSERS",
            "apikey": settings.alpha_vantage_api_key,
        }
    )
    return f"{config.endpoint_url}?{query}"


def build_alpha_vantage_global_quote_url(
    config: OfficialAPIConfig,
    symbol: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": settings.alpha_vantage_api_key,
        }
    )
    return f"{config.endpoint_url}?{query}"


def build_finnhub_company_news_url(
    config: OfficialAPIConfig,
    symbol: str,
    settings: Settings,
) -> str:
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=3)
    query = urlencode(
        {
            "symbol": symbol,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "token": settings.finnhub_api_key,
        }
    )
    return f"{config.endpoint_url}/company-news?{query}"


def build_finnhub_quote_url(
    config: OfficialAPIConfig,
    symbol: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "symbol": symbol,
            "token": settings.finnhub_api_key,
        }
    )
    return f"{config.endpoint_url}/quote?{query}"


def build_newsapi_everything_url(
    config: OfficialAPIConfig,
    query_text: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "q": query_text,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": "25",
        }
    )
    return f"{config.endpoint_url}?{query}"


def build_newsapi_top_headlines_url(
    config: OfficialAPIConfig,
    category: str,
    settings: Settings,
) -> str:
    query = urlencode(
        {
            "country": "us",
            "category": category,
            "pageSize": "25",
        }
    )
    return "https://newsapi.org/v2/top-headlines?" + query


def build_gdelt_doc_url(config: OfficialAPIConfig, query_text: str) -> str:
    query = urlencode(
        {
            "query": query_text,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": "25",
            "sort": "HybridRel",
        }
    )
    return f"{config.endpoint_url}?{query}"


def parse_xlsx_rows(workbook: bytes) -> list[list[str]]:
    try:
        with ZipFile(BytesIO(workbook)) as archive:
            shared_strings = read_xlsx_shared_strings(archive)
            sheet_name = read_xlsx_first_sheet_name(archive)
            sheet_xml = archive.read(sheet_name)
    except Exception as error:
        raise ValueError("Unable to read Freddie Mac PMMS workbook") from error

    root = ElementTree.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row in root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        cells: list[str] = []
        for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            column_index = xlsx_column_index(cell.attrib.get("r", ""))
            while len(cells) < column_index:
                cells.append("")
            cells.append(read_xlsx_cell_value(cell, shared_strings))
        rows.append(cells)
    return rows


def read_xlsx_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        parts = [
            text.text or ""
            for text in item.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        ]
        strings.append("".join(parts))
    return strings


def read_xlsx_first_sheet_name(archive: ZipFile) -> str:
    workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationship_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    first_sheet = workbook_root.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
    if first_sheet is None:
        raise ValueError("Workbook has no sheets")

    relationship_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    for relationship in relationship_root:
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib["Target"].lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"

    raise ValueError("Workbook first sheet relationship missing")


def read_xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        texts = cell.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        return "".join(text.text or "" for text in texts).strip()

    value = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if value is None or value.text is None:
        return ""

    if cell_type == "s":
        index = int(value.text)
        return shared_strings[index].strip() if index < len(shared_strings) else ""

    return value.text.strip()


def xlsx_column_index(cell_reference: str) -> int:
    letters = "".join(character for character in cell_reference if character.isalpha())
    if not letters:
        return 1

    index = 0
    for character in letters.upper():
        index = (index * 26) + (ord(character) - ord("A") + 1)
    return index


def find_pmms_header_row(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        if find_pmms_date_column(row) is not None and (
            find_pmms_rate_column(row, "30") is not None or find_pmms_rate_column(row, "15") is not None
        ):
            return index
    return None


def find_pmms_date_column(header: list[str]) -> int | None:
    for index, value in enumerate(header):
        normalized = normalize_header_text(value)
        if "date" in normalized or "week" in normalized:
            return index
    return None


def find_pmms_rate_column(header: list[str], term_years: str) -> int | None:
    for index, value in enumerate(header):
        normalized = normalize_header_text(value)
        if term_years not in normalized:
            continue
        if any(excluded in normalized for excluded in ("fee", "point", "margin")):
            continue
        if any(token in normalized for token in ("frm", "fixed", "rate")):
            return index
    return None


def normalize_header_text(value: str) -> str:
    return value.strip().lower().replace("-", " ").replace("_", " ")


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


def parse_percentage(value: Any | None) -> float | None:
    if value is None:
        return None
    return parse_float(str(value).replace("%", "").strip())


def build_quote_observations(
    config: OfficialAPIConfig,
    *,
    provider_prefix: str,
    symbol: str,
    price: float | None,
    change: float | None,
    change_percent: float | None,
    volume: float | None,
    period: str,
    retrieved_at: datetime,
    released_at: datetime | None = None,
) -> list[StructuredObservationRecord]:
    values = (
        ("PRICE", "Price", price, "currency"),
        ("CHANGE", "Change", change, "currency"),
        ("CHANGE_PERCENT", "Change Percent", change_percent, "percent"),
        ("VOLUME", "Volume", volume, "shares"),
    )
    observations: list[StructuredObservationRecord] = []
    normalized_symbol = normalize_series_part(symbol)
    for metric_key, metric_name, value, unit in values:
        if value is None:
            continue
        series_id = f"{provider_prefix}:QUOTE:{normalized_symbol}:{metric_key}"
        observations.append(
            StructuredObservationRecord(
                source_key=config.source_key,
                series_id=series_id,
                series_name=f"{provider_prefix.replace('_', ' ').title()} Quote - {symbol} {metric_name}",
                value=value,
                unit=unit,
                period=period,
                released_at=released_at or parse_iso_date(period),
                retrieved_at=retrieved_at,
                region="US Market",
                external_id=f"{series_id}:{period}",
            )
        )
    return observations


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


def parse_pmms_date(value: Any | None) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    numeric_value = parse_float(text)
    if numeric_value is not None and numeric_value > 20_000:
        excel_epoch = datetime(1899, 12, 30, tzinfo=UTC)
        return excel_epoch + timedelta(days=int(numeric_value))

    for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(text, date_format)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue

    return None


def parse_alpha_vantage_time(value: Any | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) != 15 or "T" not in text:
        return parse_iso_date(text)
    try:
        return datetime.strptime(text, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def parse_unix_timestamp(value: Any | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def parse_gdelt_seendate(value: Any | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    for date_format in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(text, date_format).replace(tzinfo=UTC)
        except ValueError:
            continue
    return parse_iso_date(text)


def optional_text(value: Any | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def stable_external_part(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def url_without_secret(url: str) -> str:
    parsed = urlsplit(url)
    safe_query = urlencode(
        [
            (key, "[redacted]" if key.lower() in {"apikey", "api_key", "token", "key"} else value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, safe_query, parsed.fragment))


def build_quarter_period(year: str, quarter: str) -> str:
    return f"{int(year)}Q{int(quarter)}"


def parse_quarter_period(year: str, quarter: str) -> datetime:
    month = ((int(quarter) - 1) * 3) + 1
    if month < 1 or month > 10:
        raise ValueError(f"Invalid quarter: {quarter}")
    return datetime(int(year), month, 1, tzinfo=UTC)


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
