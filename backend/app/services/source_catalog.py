import json
from functools import lru_cache
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.source import SourceCatalogEntry


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "source_catalog.json"
catalog_adapter = TypeAdapter(list[SourceCatalogEntry])


@lru_cache
def load_source_catalog() -> tuple[SourceCatalogEntry, ...]:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        raw_catalog = json.load(catalog_file)

    sources = catalog_adapter.validate_python(raw_catalog)
    ensure_unique_source_ids(sources)
    return tuple(sources)


def ensure_unique_source_ids(sources: list[SourceCatalogEntry]) -> None:
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()

    for source in sources:
        if source.id in seen_ids:
            duplicate_ids.add(source.id)
        seen_ids.add(source.id)

    if duplicate_ids:
        duplicates = ", ".join(sorted(duplicate_ids))
        raise ValueError(f"Duplicate source ids in source catalog: {duplicates}")


def get_source_catalog(
    *,
    enabled_only: bool = False,
    include_optional: bool = True,
) -> list[SourceCatalogEntry]:
    sources = list(load_source_catalog())

    if enabled_only:
        sources = [source for source in sources if source.enabled_by_default]

    if not include_optional:
        sources = [source for source in sources if source.phase == "v1"]

    return sources
