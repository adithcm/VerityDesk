from datetime import UTC, datetime
from html import escape
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
    build_alpha_vantage_global_quote_url,
    build_alpha_vantage_news_sentiment_url,
    build_alpha_vantage_top_gainers_losers_url,
    build_census_eits_url,
    build_fhfa_hpi_url,
    build_finnhub_company_news_url,
    build_finnhub_quote_url,
    build_fred_observations_url,
    build_gdelt_doc_url,
    build_newsapi_everything_url,
    build_newsapi_top_headlines_url,
    ingest_official_api_source,
    normalize_alpha_vantage_news_sentiment,
    normalize_alpha_vantage_global_quote,
    normalize_alpha_vantage_top_gainers_losers,
    normalize_census_eits_observations,
    normalize_fhfa_hpi_observations,
    normalize_finnhub_company_news,
    normalize_finnhub_quote,
    normalize_freddie_mac_pmms_observations,
    normalize_fred_observations,
    normalize_gdelt_doc,
    normalize_newsapi_everything,
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
FREDDIE_MAC_PMMS_SPLIT_HEADER_SAMPLE = [
    ["", "", "U.S.", "30 yr", "U.S.", "15 yr", "U.S."],
    ["", "", "30 yr", "fees &", "15 yr", "fees &", "5/1"],
    ["", "Week", "FRM", "points", "FRM", "points", "ARM"],
    ["", "46268", "6.71", "", "6.04", "", ""],
]
ALPHA_VANTAGE_NEWS_SAMPLE = {
    "feed": [
        {
            "title": "Markets watch Fed path",
            "url": "https://example.com/alpha-fed",
            "time_published": "20260907T130000",
            "source": "Example Wire",
            "source_domain": "example.com",
            "summary": "Investors are watching rate expectations.",
            "overall_sentiment_score": "0.12",
            "overall_sentiment_label": "Neutral",
            "ticker_sentiment": [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
        }
    ]
}
ALPHA_VANTAGE_TOP_MOVERS_SAMPLE = {
    "top_gainers": [{"ticker": "XYZ", "price": "12.50", "change_percentage": "8.25%"}],
    "top_losers": [{"ticker": "ABC", "price": "9.10", "change_percentage": "-5.00%"}],
    "most_actively_traded": [{"ticker": "NVDA", "price": "180.00", "change_percentage": "1.50%"}],
}
ALPHA_VANTAGE_GLOBAL_QUOTE_SAMPLE = {
    "Global Quote": {
        "01. symbol": "AAPL",
        "05. price": "250.10",
        "06. volume": "123456",
        "07. latest trading day": "2026-09-07",
        "09. change": "1.25",
        "10. change percent": "0.5025%",
    }
}
FINNHUB_COMPANY_NEWS_SAMPLE = [
    {
        "id": 101,
        "headline": "Apple supplier update",
        "summary": "Supplier demand commentary moved shares.",
        "url": "https://example.com/finnhub-apple",
        "source": "Example News",
        "datetime": 1788786000,
        "category": "company",
        "related": "AAPL",
    }
]
FINNHUB_QUOTE_SAMPLE = {"c": 250.10, "d": 1.25, "dp": 0.5025, "t": 1788795000}
NEWSAPI_EVERYTHING_SAMPLE = {
    "status": "ok",
    "totalResults": 1,
    "articles": [
        {
            "source": {"id": "example", "name": "Example News"},
            "author": "Reporter",
            "title": "Housing market cools",
            "description": "Mortgage costs weigh on demand.",
            "url": "https://example.com/newsapi-housing",
            "publishedAt": "2026-09-07T15:30:00Z",
            "content": "Mortgage costs weigh on demand. [+120 chars]",
        }
    ],
}
GDELT_DOC_SAMPLE = {
    "articles": [
        {
            "url": "https://example.com/gdelt-energy",
            "title": "Energy talks continue",
            "seendate": "20260907T153000Z",
            "domain": "example.com",
            "language": "English",
            "sourcecountry": "US",
        }
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
                f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
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


def test_normalize_freddie_mac_pmms_observations_supports_split_headers() -> None:
    records = normalize_freddie_mac_pmms_observations(
        build_config(source_key="freddie-mac-pmms", connector_kind="freddie_mac_pmms"),
        build_xlsx(FREDDIE_MAC_PMMS_SPLIT_HEADER_SAMPLE),
        datetime(2026, 9, 3, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 2
    assert records[0].series_id == "FREDDIE_PMMS:30Y_FIXED"
    assert records[0].period == "2026-09-03"
    assert records[0].value == 6.71
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


def test_normalize_alpha_vantage_news_sentiment_builds_article_records() -> None:
    records = normalize_alpha_vantage_news_sentiment(
        build_config(source_key="alpha-vantage", connector_kind="alpha_vantage_news_sentiment"),
        "financial_markets",
        ALPHA_VANTAGE_NEWS_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].source_key == "alpha-vantage"
    assert records[0].title == "Markets watch Fed path"
    assert records[0].url == "https://example.com/alpha-fed"
    assert records[0].publisher == "Example Wire"
    assert records[0].published_at == datetime(2026, 9, 7, 13, 0, tzinfo=UTC)
    assert records[0].companies == ["AAPL", "MSFT"]
    assert records[0].metadata["topic"] == "financial_markets"


def test_normalize_alpha_vantage_news_sentiment_rejects_malformed_response() -> None:
    try:
        normalize_alpha_vantage_news_sentiment(
            build_config(source_key="alpha-vantage", connector_kind="alpha_vantage_news_sentiment"),
            "financial_markets",
            {"feed": "bad"},
            datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "malformed feed" in str(error)
    else:
        raise AssertionError("Expected malformed Alpha Vantage response to raise ValueError")


def test_normalize_alpha_vantage_top_gainers_losers_builds_observations() -> None:
    records = normalize_alpha_vantage_top_gainers_losers(
        build_config(source_key="alpha-vantage", connector_kind="alpha_vantage_news_sentiment"),
        ALPHA_VANTAGE_TOP_MOVERS_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 3
    assert records[0].series_id == "ALPHA_VANTAGE:TOP_GAINERS:XYZ:CHANGE_PERCENT"
    assert records[0].series_name == "Alpha Vantage Top Gainer - XYZ Change Percent"
    assert records[0].value == 8.25
    assert records[0].unit == "percent"
    assert records[0].period == "2026-09-07"


def test_normalize_alpha_vantage_global_quote_builds_observations() -> None:
    records = normalize_alpha_vantage_global_quote(
        build_config(source_key="alpha-vantage", connector_kind="alpha_vantage_news_sentiment"),
        "AAPL",
        ALPHA_VANTAGE_GLOBAL_QUOTE_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 4
    assert records[0].series_id == "ALPHA_VANTAGE:QUOTE:AAPL:PRICE"
    assert records[0].value == 250.10
    assert records[0].period == "2026-09-07"
    assert records[2].series_id == "ALPHA_VANTAGE:QUOTE:AAPL:CHANGE_PERCENT"
    assert records[2].value == 0.5025


def test_normalize_finnhub_company_news_builds_article_records() -> None:
    records = normalize_finnhub_company_news(
        build_config(source_key="finnhub", connector_kind="finnhub_company_news"),
        "AAPL",
        FINNHUB_COMPANY_NEWS_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].source_key == "finnhub"
    assert records[0].title == "Apple supplier update"
    assert records[0].companies == ["AAPL"]
    assert records[0].external_id == "finnhub:101"
    assert records[0].metadata["symbol"] == "AAPL"


def test_normalize_finnhub_company_news_rejects_malformed_response() -> None:
    try:
        normalize_finnhub_company_news(
            build_config(source_key="finnhub", connector_kind="finnhub_company_news"),
            "AAPL",
            {"bad": "shape"},
            datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "must be a list" in str(error)
    else:
        raise AssertionError("Expected malformed Finnhub response to raise ValueError")


def test_normalize_finnhub_quote_builds_observations() -> None:
    records = normalize_finnhub_quote(
        build_config(source_key="finnhub", connector_kind="finnhub_company_news"),
        "AAPL",
        FINNHUB_QUOTE_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 3
    assert records[0].series_id == "FINNHUB:QUOTE:AAPL:PRICE"
    assert records[0].value == 250.10
    assert records[1].series_id == "FINNHUB:QUOTE:AAPL:CHANGE"
    assert records[2].series_id == "FINNHUB:QUOTE:AAPL:CHANGE_PERCENT"


def test_normalize_newsapi_everything_builds_article_records() -> None:
    records = normalize_newsapi_everything(
        build_config(source_key="newsapi", connector_kind="newsapi_everything"),
        "housing market",
        NEWSAPI_EVERYTHING_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].source_key == "newsapi"
    assert records[0].title == "Housing market cools"
    assert records[0].publisher == "Example News"
    assert records[0].published_at == datetime(2026, 9, 7, 15, 30, tzinfo=UTC)
    assert records[0].metadata["query"] == "housing market"


def test_normalize_newsapi_everything_rejects_error_response() -> None:
    try:
        normalize_newsapi_everything(
            build_config(source_key="newsapi", connector_kind="newsapi_everything"),
            "markets",
            {"status": "error", "message": "bad key"},
            datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "bad key" in str(error)
    else:
        raise AssertionError("Expected NewsAPI error response to raise ValueError")


def test_normalize_gdelt_doc_builds_article_records() -> None:
    records = normalize_gdelt_doc(
        build_config(source_key="gdelt-cloud", connector_kind="gdelt_doc"),
        "geopolitics energy",
        GDELT_DOC_SAMPLE,
        datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )

    assert len(records) == 1
    assert records[0].source_key == "gdelt-cloud"
    assert records[0].title == "Energy talks continue"
    assert records[0].publisher == "US"
    assert records[0].published_at == datetime(2026, 9, 7, 15, 30, tzinfo=UTC)
    assert records[0].metadata["query"] == "geopolitics energy"


def test_normalize_gdelt_doc_rejects_malformed_response() -> None:
    try:
        normalize_gdelt_doc(
            build_config(source_key="gdelt-cloud", connector_kind="gdelt_doc"),
            "markets",
            {"articles": "bad"},
            datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "malformed articles" in str(error)
    else:
        raise AssertionError("Expected malformed GDELT response to raise ValueError")


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


def test_ingest_census_continues_when_one_dataset_returns_empty_body(monkeypatch) -> None:
    config = build_config(
        source_key="census-economic-indicators",
        source_name="U.S. Census Economic Indicators",
        connector_kind="census_eits",
        endpoint_url="https://api.census.gov/data/timeseries/eits",
        required_api_key_setting="census_api_key",
        default_identifiers=("mhs", "ressales"),
    )

    def fake_fetch_json(url: str, settings: Settings):
        if "/mhs?" in url:
            raise ValueError("Expected JSON from Census, but received: empty response body")
        if "/ressales?" in url:
            return CENSUS_EITS_SAMPLE
        raise AssertionError(f"Unexpected Census URL: {url}")

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(census_api_key="test-key"))

        observation = session.scalar(select(EconomicObservation))
        run = session.scalar(select(IngestionRun))
        health = session.scalar(select(SourceHealth))

        assert result.status == "success"
        assert result.items_seen == 1
        assert result.items_skipped == 1
        assert result.error is not None
        assert "mhs:" in result.error
        assert observation is not None
        assert run is not None
        assert run.status == "success"
        assert health is not None
        assert health.status == "fresh"


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


def test_keyed_optional_provider_skips_without_api_key() -> None:
    config = build_config(
        source_key="alpha-vantage",
        source_name="Alpha Vantage",
        connector_kind="alpha_vantage_news_sentiment",
        endpoint_url="https://www.alphavantage.co/query",
        required_api_key_setting="alpha_vantage_api_key",
        default_identifiers=("financial_markets",),
    )

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(alpha_vantage_api_key=None))

        run = session.scalar(select(IngestionRun))
        health = session.scalar(select(SourceHealth))

        assert result.status == "skipped"
        assert result.error == "Missing required API key setting: ALPHA_VANTAGE_API_KEY"
        assert run is not None
        assert run.status == "skipped"
        assert health is not None
        assert health.status == "skipped"


def test_ingest_alpha_vantage_news_sentiment_persists_articles(monkeypatch) -> None:
    config = build_config(
        source_key="alpha-vantage",
        source_name="Alpha Vantage",
        connector_kind="alpha_vantage_news_sentiment",
        endpoint_url="https://www.alphavantage.co/query",
        required_api_key_setting="alpha_vantage_api_key",
        default_identifiers=("financial_markets",),
    )

    def fake_fetch_json(url: str, settings: Settings):
        assert "apikey=test-key" in url
        if "function=NEWS_SENTIMENT" in url:
            assert "topics=financial_markets" in url
            return ALPHA_VANTAGE_NEWS_SAMPLE
        if "function=TOP_GAINERS_LOSERS" in url:
            return ALPHA_VANTAGE_TOP_MOVERS_SAMPLE
        if "function=GLOBAL_QUOTE" in url:
            return ALPHA_VANTAGE_GLOBAL_QUOTE_SAMPLE
        raise AssertionError(f"Unexpected Alpha Vantage URL: {url}")

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(alpha_vantage_api_key="test-key"))

        article = session.scalar(select(Article))
        observations = session.scalars(select(EconomicObservation)).all()
        external_id = session.scalar(select(ExternalID))

        assert result.status == "success"
        assert result.items_inserted == 20
        assert article is not None
        assert article.title == "Markets watch Fed path"
        assert article.companies == ["AAPL", "MSFT"]
        assert len(observations) == 19
        assert external_id is not None
        assert external_id.article_id == article.id


def test_ingest_finnhub_company_news_persists_articles(monkeypatch) -> None:
    config = build_config(
        source_key="finnhub",
        source_name="Finnhub",
        connector_kind="finnhub_company_news",
        endpoint_url="https://finnhub.io/api/v1",
        required_api_key_setting="finnhub_api_key",
        default_identifiers=("AAPL",),
    )

    def fake_fetch_json(url: str, settings: Settings):
        assert "token=test-key" in url
        if "/company-news?" in url:
            assert "symbol=AAPL" in url
            return FINNHUB_COMPANY_NEWS_SAMPLE
        if "/quote?" in url:
            assert "symbol=AAPL" in url
            return FINNHUB_QUOTE_SAMPLE
        raise AssertionError(f"Unexpected Finnhub URL: {url}")

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(finnhub_api_key="test-key"))

        article = session.scalar(select(Article))
        observations = session.scalars(select(EconomicObservation)).all()

        assert result.status == "success"
        assert result.items_inserted == 4
        assert article is not None
        assert article.title == "Apple supplier update"
        assert article.companies == ["AAPL"]
        assert len(observations) == 3


def test_ingest_newsapi_everything_persists_articles(monkeypatch) -> None:
    config = build_config(
        source_key="newsapi",
        source_name="NewsAPI",
        connector_kind="newsapi_everything",
        endpoint_url="https://newsapi.org/v2/everything",
        required_api_key_setting="newsapi_key",
        default_identifiers=("housing market",),
    )

    def fake_fetch_json(url: str, settings: Settings):
        assert "q=housing+market" in url or "top-headlines" in url
        assert settings.newsapi_key == "test-key"
        return NEWSAPI_EVERYTHING_SAMPLE

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        result = ingest_official_api_source(session, config, settings=Settings(newsapi_key="test-key"))

        article = session.scalar(select(Article))

        assert result.status == "success"
        assert result.items_inserted == 1
        assert result.items_updated == 3
        assert article is not None
        assert article.title == "Housing market cools"


def test_ingest_gdelt_doc_persists_articles_without_api_key(monkeypatch) -> None:
    config = build_config(
        source_key="gdelt-cloud",
        source_name="GDELT Cloud",
        connector_kind="gdelt_doc",
        endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc",
        default_identifiers=("geopolitics energy",),
    )

    def fake_fetch_json(url: str, settings: Settings):
        assert "query=geopolitics+energy" in url
        assert "format=json" in url
        return GDELT_DOC_SAMPLE

    monkeypatch.setattr(official_api_ingestion, "fetch_json", fake_fetch_json)

    with build_session() as session:
        first_result = ingest_official_api_source(session, config)
        second_result = ingest_official_api_source(session, config)

        articles = session.scalars(select(Article)).all()

        assert first_result.status == "success"
        assert first_result.items_inserted == 1
        assert second_result.items_inserted == 0
        assert second_result.items_updated == 1
        assert len(articles) == 1


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


def test_build_optional_provider_urls_include_expected_parameters() -> None:
    alpha_url = build_alpha_vantage_news_sentiment_url(
        build_config(
            source_key="alpha-vantage",
            connector_kind="alpha_vantage_news_sentiment",
            endpoint_url="https://www.alphavantage.co/query",
        ),
        "real_estate",
        Settings(alpha_vantage_api_key="alpha-key"),
    )
    alpha_top_movers_url = build_alpha_vantage_top_gainers_losers_url(
        build_config(
            source_key="alpha-vantage",
            connector_kind="alpha_vantage_news_sentiment",
            endpoint_url="https://www.alphavantage.co/query",
        ),
        Settings(alpha_vantage_api_key="alpha-key"),
    )
    alpha_quote_url = build_alpha_vantage_global_quote_url(
        build_config(
            source_key="alpha-vantage",
            connector_kind="alpha_vantage_news_sentiment",
            endpoint_url="https://www.alphavantage.co/query",
        ),
        "AAPL",
        Settings(alpha_vantage_api_key="alpha-key"),
    )
    finnhub_url = build_finnhub_company_news_url(
        build_config(
            source_key="finnhub",
            connector_kind="finnhub_company_news",
            endpoint_url="https://finnhub.io/api/v1",
        ),
        "AAPL",
        Settings(finnhub_api_key="finnhub-key"),
    )
    finnhub_quote_url = build_finnhub_quote_url(
        build_config(
            source_key="finnhub",
            connector_kind="finnhub_company_news",
            endpoint_url="https://finnhub.io/api/v1",
        ),
        "AAPL",
        Settings(finnhub_api_key="finnhub-key"),
    )
    newsapi_url = build_newsapi_everything_url(
        build_config(
            source_key="newsapi",
            connector_kind="newsapi_everything",
            endpoint_url="https://newsapi.org/v2/everything",
        ),
        "housing market",
        Settings(newsapi_key="news-key"),
    )
    newsapi_headlines_url = build_newsapi_top_headlines_url(
        build_config(
            source_key="newsapi",
            connector_kind="newsapi_everything",
            endpoint_url="https://newsapi.org/v2/everything",
        ),
        "business",
        Settings(newsapi_key="news-key"),
    )
    gdelt_url = build_gdelt_doc_url(
        build_config(
            source_key="gdelt-cloud",
            connector_kind="gdelt_doc",
            endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc",
        ),
        "geopolitics energy",
    )

    assert "function=NEWS_SENTIMENT" in alpha_url
    assert "topics=real_estate" in alpha_url
    assert "apikey=alpha-key" in alpha_url
    assert "function=TOP_GAINERS_LOSERS" in alpha_top_movers_url
    assert "function=GLOBAL_QUOTE" in alpha_quote_url
    assert "symbol=AAPL" in alpha_quote_url
    assert "/company-news?" in finnhub_url
    assert "symbol=AAPL" in finnhub_url
    assert "token=finnhub-key" in finnhub_url
    assert "/quote?" in finnhub_quote_url
    assert "q=housing+market" in newsapi_url
    assert "top-headlines" in newsapi_headlines_url
    assert "category=business" in newsapi_headlines_url
    assert "query=geopolitics+energy" in gdelt_url
    assert "maxrecords=25" in gdelt_url


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
