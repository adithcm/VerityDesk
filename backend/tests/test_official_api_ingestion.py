from datetime import UTC, datetime
from io import BytesIO
from zipfile import ZipFile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Article, EconomicObservation, ExternalID, IngestionRun, SourceHealth
from app.services import official_api_ingestion
from app.services.official_api_ingestion import (
    OfficialAPIConfig,
    build_census_eits_url,
    build_fhfa_hpi_url,
    build_fred_observations_url,
    ingest_official_api_source,
    normalize_census_eits_observations,
    normalize_fhfa_hpi_observations,
    normalize_freddie_mac_pmms_observations,
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


CENSUS_EITS_SAMPLE = [
    ["data_type_code", "time_slot_id", "seasonally_adj", "category_code", "cell_value", "error_data", "time", "us"],
    ["TOTAL", "1", "yes", "SOLD", "685", "no", "2026-08", "1"],
    ["TOTAL", "1", "yes", "SOLD", "NA", "no", "2026-07", "1"],
]


FHFA_STATE_SAMPLE = "AZ\t2026\t1\t450.10\nAZ\t2026\t2\t451.25\nCA\t2026\t2\t-\n"
FHFA_US_CENSUS_SAMPLE = "USA\t2026\t2\t410.50\nDV_MTN\t2026\t2\t500.25\n"
FHFA_METRO_SAMPLE = '"Phoenix-Mesa-Chandler, AZ"\t38060\t2026\t2\t350.44\t( 4.12)\nAbilene, TX\t10180\t1975\t1\t-\t-\n'
FREDDIE_MAC_PMMS_SAMPLE = [
    ["Week", "30-Yr FRM", "30-Yr Fees/Points", "15-Yr FRM", "15-Yr Fees/Points"],
    ["2026-09-03", "6.71", "", "6.04", ""],
    ["2026-08-27", "6.66", "", "5.98", ""],
]


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


def build_xlsx(rows: list[list[str]]) -> bytes:
    def column_name(index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(ord("A") + remainder) + name
        return name

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t>{value}</t></is></c>'
                if value
                else f'<c r="{reference}"/>'
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="PMMS" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


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


def test_normalize_census_eits_observations_builds_structured_records() -> None:
    records = normalize_census_eits_observations(
        build_config(source_key="census-economic-indicators", connector_kind="census_eits"),
        "ressales",
        CENSUS_EITS_SAMPLE,
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].source_key == "census-economic-indicators"
    assert records[0].series_id == "CENSUS_EITS:RESSALES:TOTAL:SOLD:YES:1"
    assert records[0].series_name == "New Residential Sales - TOTAL - SOLD (seasonally adjusted)"
    assert records[0].value == 685.0
    assert records[0].period == "2026-08"
    assert records[0].region == "US"
    assert records[0].external_id == "CENSUS_EITS:RESSALES:TOTAL:SOLD:YES:1:2026-08:US"


def test_normalize_census_eits_observations_allows_empty_response() -> None:
    records = normalize_census_eits_observations(
        build_config(source_key="census-economic-indicators", connector_kind="census_eits"),
        "mhs",
        [],
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert records == []


def test_normalize_census_eits_observations_rejects_malformed_response() -> None:
    try:
        normalize_census_eits_observations(
            build_config(source_key="census-economic-indicators", connector_kind="census_eits"),
            "mhs",
            [["data_type_code"], ["TOTAL"]],
            datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "missing required columns" in str(error)
    else:
        raise AssertionError("Expected malformed Census response to raise ValueError")


def test_normalize_fhfa_state_observations_builds_structured_records() -> None:
    records = normalize_fhfa_hpi_observations(
        build_config(source_key="fhfa-hpi", connector_kind="fhfa_hpi"),
        "state",
        FHFA_STATE_SAMPLE,
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 2
    assert records[0].source_key == "fhfa-hpi"
    assert records[0].series_id == "FHFA_HPI:STATE:AZ"
    assert records[0].series_name == "FHFA All-Transactions HPI - Arizona"
    assert records[0].value == 450.10
    assert records[0].period == "2026Q1"
    assert records[0].released_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert records[0].region == "Arizona"
    assert records[0].external_id == "FHFA_HPI:STATE:AZ:2026Q1"


def test_normalize_fhfa_us_census_observations_builds_structured_records() -> None:
    records = normalize_fhfa_hpi_observations(
        build_config(source_key="fhfa-hpi", connector_kind="fhfa_hpi"),
        "us_census",
        FHFA_US_CENSUS_SAMPLE,
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 2
    assert records[0].series_id == "FHFA_HPI:US_CENSUS:USA"
    assert records[0].series_name == "FHFA All-Transactions HPI - United States"
    assert records[0].value == 410.50
    assert records[0].period == "2026Q2"
    assert records[0].region == "United States"
    assert records[1].series_name == "FHFA All-Transactions HPI - Mountain"


def test_normalize_fhfa_metro_observations_builds_structured_records() -> None:
    records = normalize_fhfa_hpi_observations(
        build_config(source_key="fhfa-hpi", connector_kind="fhfa_hpi"),
        "metro",
        FHFA_METRO_SAMPLE,
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].series_id == "FHFA_HPI:METRO:38060"
    assert records[0].series_name == "FHFA All-Transactions HPI - Phoenix-Mesa-Chandler, AZ"
    assert records[0].value == 350.44
    assert records[0].period == "2026Q2"
    assert records[0].region == "Phoenix-Mesa-Chandler, AZ"


def test_normalize_fhfa_hpi_observations_allows_empty_response() -> None:
    records = normalize_fhfa_hpi_observations(
        build_config(source_key="fhfa-hpi", connector_kind="fhfa_hpi"),
        "state",
        "",
        datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
    )

    assert records == []


def test_normalize_fhfa_hpi_observations_rejects_malformed_response() -> None:
    try:
        normalize_fhfa_hpi_observations(
            build_config(source_key="fhfa-hpi", connector_kind="fhfa_hpi"),
            "metro",
            "Phoenix-Mesa-Chandler, AZ\t38060\t2026\n",
            datetime(2026, 9, 2, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "missing required columns" in str(error)
    else:
        raise AssertionError("Expected malformed FHFA response to raise ValueError")


def test_normalize_freddie_mac_pmms_observations_builds_structured_records() -> None:
    records = normalize_freddie_mac_pmms_observations(
        build_config(source_key="freddie-mac-pmms", connector_kind="freddie_mac_pmms"),
        build_xlsx(FREDDIE_MAC_PMMS_SAMPLE),
        datetime(2026, 9, 3, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 4
    assert records[0].source_key == "freddie-mac-pmms"
    assert records[0].series_id == "FREDDIE_PMMS:30Y_FIXED"
    assert records[0].series_name == "Freddie Mac PMMS - 30-Year Fixed-Rate Mortgage"
    assert records[0].value == 6.71
    assert records[0].unit == "percent"
    assert records[0].period == "2026-09-03"
    assert records[0].released_at == datetime(2026, 9, 3, tzinfo=UTC)
    assert records[0].region == "United States"
    assert records[0].external_id == "FREDDIE_PMMS:30Y_FIXED:2026-09-03"
    assert records[1].series_id == "FREDDIE_PMMS:15Y_FIXED"
    assert records[1].value == 6.04


def test_normalize_freddie_mac_pmms_observations_allows_empty_workbook() -> None:
    records = normalize_freddie_mac_pmms_observations(
        build_config(source_key="freddie-mac-pmms", connector_kind="freddie_mac_pmms"),
        build_xlsx([]),
        datetime(2026, 9, 3, 16, 0, tzinfo=UTC),
    )

    assert records == []


def test_normalize_freddie_mac_pmms_observations_rejects_malformed_workbook() -> None:
    try:
        normalize_freddie_mac_pmms_observations(
            build_config(source_key="freddie-mac-pmms", connector_kind="freddie_mac_pmms"),
            build_xlsx([["Week", "No Rate"], ["2026-09-03", "6.71"]]),
            datetime(2026, 9, 3, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "missing date and mortgage rate columns" in str(error)
    else:
        raise AssertionError("Expected malformed Freddie Mac PMMS workbook to raise ValueError")


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


def test_ingest_census_skips_without_api_key() -> None:
    config = build_config(
        source_key="census-economic-indicators",
        source_name="U.S. Census Economic Indicators",
        connector_kind="census_eits",
        endpoint_url="https://api.census.gov/data/timeseries/eits",
        required_api_key_setting="census_api_key",
        default_identifiers=("ressales",),
    )

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(census_api_key=None))

        run = session.scalar(select(IngestionRun))
        health = session.scalar(select(SourceHealth))

        assert result.status == "skipped"
        assert result.error == "Missing required API key setting: CENSUS_API_KEY"
        assert run is not None
        assert run.status == "skipped"
        assert health is not None
        assert health.status == "skipped"


def test_ingest_census_persists_structured_observations(monkeypatch) -> None:
    config = build_config(
        source_key="census-economic-indicators",
        source_name="U.S. Census Economic Indicators",
        connector_kind="census_eits",
        endpoint_url="https://api.census.gov/data/timeseries/eits",
        required_api_key_setting="census_api_key",
        default_identifiers=("ressales",),
    )

    def fake_fetch_json(url: str, settings: Settings):
        assert "/ressales?" in url
        assert "key=test-key" in url
        return CENSUS_EITS_SAMPLE

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(census_api_key="test-key"))

        observation = session.scalar(select(EconomicObservation))
        external_id = session.scalar(select(ExternalID))

        assert result.status == "success"
        assert result.items_seen == 1
        assert result.items_inserted == 1
        assert observation is not None
        assert observation.series_id == "CENSUS_EITS:RESSALES:TOTAL:SOLD:YES:1"
        assert observation.region == "US"
        assert external_id is not None
        assert external_id.observation_id == observation.id


def test_ingest_fhfa_hpi_persists_structured_observations_and_dedupes(monkeypatch) -> None:
    config = build_config(
        source_key="fhfa-hpi",
        source_name="FHFA House Price Index",
        connector_kind="fhfa_hpi",
        endpoint_url="https://www.fhfa.gov/hpi/download/quarterly_datasets",
        default_identifiers=("state",),
    )

    def fake_fetch_text(url: str, settings: Settings):
        assert url == "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.txt"
        return FHFA_STATE_SAMPLE

    monkeypatch.setattr(official_api_ingestion, "fetch_text", fake_fetch_text)

    with build_session() as session:
        first_result = ingest_official_api_source(session, config)
        second_result = ingest_official_api_source(session, config)

        observations = session.scalars(select(EconomicObservation)).all()
        external_ids = session.scalars(select(ExternalID)).all()

        assert first_result.status == "success"
        assert first_result.items_seen == 2
        assert first_result.items_inserted == 2
        assert second_result.items_inserted == 0
        assert second_result.items_updated == 2
        assert len(observations) == 2
        assert observations[0].series_id == "FHFA_HPI:STATE:AZ"
        assert len(external_ids) == 2


def test_ingest_freddie_mac_pmms_persists_structured_observations_and_dedupes(monkeypatch) -> None:
    config = build_config(
        source_key="freddie-mac-pmms",
        source_name="Freddie Mac PMMS",
        connector_kind="freddie_mac_pmms",
        endpoint_url="https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx",
        default_identifiers=("30_year_fixed", "15_year_fixed"),
    )

    def fake_fetch_bytes(url: str, settings: Settings):
        assert url == "https://www.freddiemac.com/pmms/docs/historicalweeklydata.xlsx"
        return build_xlsx(FREDDIE_MAC_PMMS_SAMPLE)

    monkeypatch.setattr(official_api_ingestion, "fetch_bytes", fake_fetch_bytes)

    with build_session() as session:
        first_result = ingest_official_api_source(session, config)
        second_result = ingest_official_api_source(session, config)

        observations = session.scalars(select(EconomicObservation)).all()
        health = session.scalar(select(SourceHealth))

        assert first_result.status == "success"
        assert first_result.items_seen == 4
        assert first_result.items_inserted == 4
        assert second_result.items_inserted == 0
        assert second_result.items_updated == 4
        assert len(observations) == 4
        assert observations[0].series_id == "FREDDIE_PMMS:30Y_FIXED"
        assert health is not None
        assert health.status == "fresh"


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


def test_build_census_eits_url_includes_key_and_dataset() -> None:
    url = build_census_eits_url(
        build_config(
            source_key="census-economic-indicators",
            connector_kind="census_eits",
            endpoint_url="https://api.census.gov/data/timeseries/eits",
        ),
        "mhs",
        Settings(census_api_key="test-key"),
    )

    assert url.startswith("https://api.census.gov/data/timeseries/eits/mhs?")
    assert "cell_value" in url
    assert "for=us%3A%2A" in url
    assert "key=test-key" in url


def test_build_fhfa_hpi_url_returns_public_download_url() -> None:
    assert build_fhfa_hpi_url("state") == "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.txt"


def test_placeholder_dataset_connector_logs_skipped_status() -> None:
    config = build_config(
        source_key="freddie-mac-pmms",
        source_name="Freddie Mac PMMS",
        connector_kind="freddie_mac_placeholder",
        endpoint_url="https://www.freddiemac.com/pmms",
        default_identifiers=(),
    )

    with build_session() as session:
        result = ingest_official_api_source(session, config)

        assert result.status == "skipped"
        assert "connector scaffolded" in (result.error or "")
