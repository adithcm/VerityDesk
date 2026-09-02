from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Article, EconomicObservation, ExternalID, IngestionRun, SourceHealth
from app.services import official_api_ingestion
from app.services.official_api_ingestion import (
    OfficialAPIConfig,
    build_fred_observations_url,
    ingest_official_api_source,
    normalize_fred_observations,
    normalize_sec_submissions,
)


SEC_SUBMISSIONS_SAMPLE = {
    "cik": 320193,
    "name": "Apple Inc.",
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
            "form": ["10-K", "8-K"],
            "filingDate": ["2026-09-01", "2026-09-02"],
            "reportDate": ["2026-08-31", "2026-09-02"],
            "primaryDocument": ["aapl-20260831.htm", "aapl-20260902.htm"],
            "primaryDocDescription": ["Annual report", "Current report"],
        }
    },
}


FRED_OBSERVATIONS_SAMPLE = {
    "observations": [
        {"date": "2026-08-01", "value": "4.50", "realtime_end": "2026-09-02"},
        {"date": "2026-07-01", "value": ".", "realtime_end": "2026-09-02"},
    ]
}


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def build_config(
    *,
    source_key: str = "sec-data-apis",
    source_name: str = "SEC data APIs",
    connector_kind: str = "sec_submissions",
    endpoint_url: str | None = "https://data.sec.gov/submissions/CIK{identifier}.json",
    required_api_key_setting: str | None = None,
    default_identifiers: tuple[str, ...] = ("0000320193",),
) -> OfficialAPIConfig:
    return OfficialAPIConfig(
        source_key=source_key,
        source_name=source_name,
        base_url="https://data.sec.gov",
        endpoint_url=endpoint_url,
        domains=("Companies and Earnings", "Regulation and Legal"),
        source_type="official_api",
        access_method="api",
        update_cadence="daily",
        reliability_tier="primary",
        storage_policy="structured_data",
        enabled=True,
        connector_kind=connector_kind,  # type: ignore[arg-type]
        required_api_key_setting=required_api_key_setting,
        default_identifiers=default_identifiers,
    )


def test_normalize_sec_submissions_builds_filing_records() -> None:
    records = normalize_sec_submissions(
        build_config(),
        SEC_SUBMISSIONS_SAMPLE,
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 2
    assert records[0].title == "10-K - Apple Inc."
    assert records[0].cik == "0000320193"
    assert records[0].url == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/aapl-20260831.htm"
    )
    assert records[0].content_hash


def test_normalize_fred_observations_skips_missing_values() -> None:
    records = normalize_fred_observations(
        build_config(source_key="fred-api", connector_kind="fred_observations"),
        "FEDFUNDS",
        FRED_OBSERVATIONS_SAMPLE,
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].series_id == "FEDFUNDS"
    assert records[0].value == 4.5
    assert records[0].period == "2026-08-01"
    assert records[0].external_id == "FEDFUNDS:2026-08-01:2026-09-02"


def test_ingest_sec_submissions_persists_filings_and_dedupes(monkeypatch) -> None:
    def fake_fetch_json(url: str, settings: Settings):
        assert url == "https://data.sec.gov/submissions/CIK0000320193.json"
        return SEC_SUBMISSIONS_SAMPLE

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        first_result = ingest_official_api_source(session, build_config())
        second_result = ingest_official_api_source(session, build_config())

        articles = session.scalars(select(Article)).all()
        external_ids = session.scalars(select(ExternalID)).all()
        runs = session.scalars(select(IngestionRun)).all()
        health = session.scalar(select(SourceHealth))

        assert first_result.status == "success"
        assert first_result.items_inserted == 2
        assert second_result.items_inserted == 0
        assert second_result.items_updated == 2
        assert len(articles) == 2
        assert len(external_ids) == 2
        assert len(runs) == 2
        assert health is not None
        assert health.status == "fresh"


def test_ingest_fred_skips_without_api_key() -> None:
    config = build_config(
        source_key="fred-api",
        source_name="FRED API",
        connector_kind="fred_observations",
        endpoint_url="https://api.stlouisfed.org/fred/series/observations",
        required_api_key_setting="fred_api_key",
        default_identifiers=("FEDFUNDS",),
    )

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(fred_api_key=None))

        run = session.scalar(select(IngestionRun))
        health = session.scalar(select(SourceHealth))

        assert result.status == "skipped"
        assert result.error == "Missing required API key setting: FRED_API_KEY"
        assert run is not None
        assert run.status == "skipped"
        assert health is not None
        assert health.status == "skipped"


def test_ingest_fred_persists_structured_observations(monkeypatch) -> None:
    config = build_config(
        source_key="fred-api",
        source_name="FRED API",
        connector_kind="fred_observations",
        endpoint_url="https://api.stlouisfed.org/fred/series/observations",
        required_api_key_setting="fred_api_key",
        default_identifiers=("FEDFUNDS",),
    )

    def fake_fetch_json(url: str, settings: Settings):
        assert "series_id=FEDFUNDS" in url
        assert "api_key=test-key" in url
        return FRED_OBSERVATIONS_SAMPLE

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(fred_api_key="test-key"))

        observation = session.scalar(select(EconomicObservation))
        external_id = session.scalar(select(ExternalID))

        assert result.status == "success"
        assert result.items_seen == 1
        assert result.items_inserted == 1
        assert observation is not None
        assert observation.series_id == "FEDFUNDS"
        assert observation.value == 4.5
        assert external_id is not None
        assert external_id.observation_id == observation.id


def test_build_fred_observations_url_includes_key_and_limit() -> None:
    url = build_fred_observations_url(
        build_config(
            source_key="fred-api",
            connector_kind="fred_observations",
            endpoint_url="https://api.stlouisfed.org/fred/series/observations",
        ),
        "MORTGAGE30US",
        Settings(fred_api_key="test-key"),
    )

    assert url.startswith("https://api.stlouisfed.org/fred/series/observations?")
    assert "series_id=MORTGAGE30US" in url
    assert "api_key=test-key" in url
    assert "limit=12" in url


def test_placeholder_dataset_connector_logs_skipped_status() -> None:
    config = build_config(
        source_key="fhfa-hpi",
        source_name="FHFA House Price Index",
        connector_kind="fhfa_placeholder",
        endpoint_url="https://www.fhfa.gov/house-price-index",
        default_identifiers=(),
    )

    with build_session() as session:
        result = ingest_official_api_source(session, config)

        assert result.status == "skipped"
        assert "connector scaffolded" in (result.error or "")
