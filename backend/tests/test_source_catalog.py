import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.source import SourceCatalogEntry
from app.services.source_catalog import ensure_unique_source_ids, get_source_catalog


client = TestClient(app)


def test_source_catalog_loads_v1_sources() -> None:
    sources = get_source_catalog()
    source_ids = {source.id for source in sources}

    assert len(sources) == 12
    assert "bbc-news-rss" in source_ids
    assert "sec-data-apis" in source_ids
    assert "fred-api" in source_ids
    assert "freddie-mac-pmms" in source_ids


def test_source_catalog_can_exclude_optional_sources() -> None:
    sources = get_source_catalog(include_optional=False)

    assert {source.phase for source in sources} == {"v1"}
    assert "alpha-vantage" not in {source.id for source in sources}


def test_source_catalog_can_filter_to_enabled_sources() -> None:
    sources = get_source_catalog(enabled_only=True)

    assert sources
    assert all(source.enabled_by_default for source in sources)


def test_source_catalog_rejects_duplicate_ids() -> None:
    source = SourceCatalogEntry(
        id="duplicate-source",
        name="Duplicate Source",
        base_url="https://example.com",
        source_type="official_api",
        domains=["Markets and Rates"],
        access_method="api",
        requires_api_key=False,
        requires_license=False,
        allows_full_text_storage=False,
        allows_redistribution=False,
        storage_policy="metadata_only",
        update_cadence="daily",
        reliability_tier="standard",
        enabled_by_default=True,
        phase="v1",
        status="planned",
        notes="Test fixture.",
    )

    with pytest.raises(ValueError, match="Duplicate source ids"):
        ensure_unique_source_ids([source, source])


def test_sources_endpoint_returns_catalog_summary() -> None:
    response = client.get("/api/v1/sources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 12
    assert payload["enabled_by_default_count"] == 8
    assert payload["optional_count"] == 4
    assert payload["sources"][0]["id"] == "bbc-news-rss"


def test_sources_endpoint_supports_filters() -> None:
    response = client.get("/api/v1/sources?enabled_only=true&include_optional=false")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 8
    assert payload["optional_count"] == 0
    assert all(source["enabled_by_default"] for source in payload["sources"])
