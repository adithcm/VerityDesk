from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal[
    "official_api",
    "official_dataset",
    "official_rss",
    "official_webpage",
    "licensed_api",
    "public_api",
]

AccessMethod = Literal[
    "api",
    "dataset_download",
    "rss",
    "rss_or_webpage",
]

ReliabilityTier = Literal["primary", "standard", "discovery"]
SourcePhase = Literal["v1", "optional_v1"]
SourceStatus = Literal["planned", "optional", "active", "disabled"]
StoragePolicy = Literal[
    "metadata_only",
    "metadata_and_excerpt",
    "metadata_and_structured_values",
    "structured_data",
]


class SourceCatalogEntry(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    base_url: str | None = None
    source_type: SourceType
    domains: list[str] = Field(min_length=1)
    access_method: AccessMethod
    requires_api_key: bool
    requires_license: bool
    allows_full_text_storage: bool
    allows_redistribution: bool
    storage_policy: StoragePolicy
    update_cadence: str
    reliability_tier: ReliabilityTier
    enabled_by_default: bool
    phase: SourcePhase
    status: SourceStatus
    notes: str


class SourceCatalogResponse(BaseModel):
    sources: list[SourceCatalogEntry]
    total: int
    enabled_by_default_count: int
    optional_count: int
