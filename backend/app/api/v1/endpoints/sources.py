from fastapi import APIRouter, Query

from app.schemas.source import SourceCatalogResponse
from app.services.source_catalog import get_source_catalog


router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=SourceCatalogResponse)
def list_sources(
    enabled_only: bool = Query(default=False),
    include_optional: bool = Query(default=True),
) -> SourceCatalogResponse:
    sources = get_source_catalog(
        enabled_only=enabled_only,
        include_optional=include_optional,
    )
    return SourceCatalogResponse(
        sources=sources,
        total=len(sources),
        enabled_by_default_count=sum(source.enabled_by_default for source in sources),
        optional_count=sum(source.phase == "optional_v1" for source in sources),
    )
