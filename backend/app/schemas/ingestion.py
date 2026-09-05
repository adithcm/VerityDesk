from typing import Literal

from pydantic import BaseModel, Field


IngestionRunMode = Literal["all", "rss", "official_api"]
IngestionRunStatus = Literal["success", "partial_success", "failed", "already_running"]
SourceFreshnessStatus = Literal["fresh", "stale", "failed", "skipped", "not_configured"]


class IngestionRunRequest(BaseModel):
    mode: IngestionRunMode = "all"
    source_keys: list[str] = Field(default_factory=list)


class IngestionSourceResult(BaseModel):
    source_key: str
    source_type: str
    status: str
    items_seen: int
    items_inserted: int
    items_updated: int
    items_skipped: int
    error: str | None = None


class IngestionRunResponse(BaseModel):
    request_id: str
    mode: IngestionRunMode
    status: IngestionRunStatus
    started_at: str
    completed_at: str | None = None
    results: list[IngestionSourceResult]
    message: str


class DailyScheduleConfig(BaseModel):
    enabled: bool = False
    local_time: str = "08:00"
    timezone: str = "local"
    mode: IngestionRunMode = "all"


class SourceHealthItem(BaseModel):
    source_key: str
    source_name: str | None = None
    status: SourceFreshnessStatus
    stored_status: str | None = None
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    latest_item_published_at: str | None = None
    latest_item_title: str | None = None
    consecutive_failures: int = 0
    freshness_window_hours: int = 24
    stale_after: str | None = None
    last_error: str | None = None


class SourceHealthResponse(BaseModel):
    sources: list[SourceHealthItem]
    total: int
    fresh_count: int
    stale_count: int
    failed_count: int
    skipped_count: int
    not_configured_count: int


class IngestionRunRecord(BaseModel):
    id: int
    source_key: str
    source_name: str | None = None
    run_type: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    items_seen: int
    items_inserted: int
    items_updated: int
    items_skipped: int
    error: str | None = None


class IngestionRunHistoryResponse(BaseModel):
    runs: list[IngestionRunRecord]
    total: int


class LatestIngestedItem(BaseModel):
    item_type: Literal["article", "economic_observation"]
    source_key: str
    source_name: str | None = None
    series_id: str | None = None
    title: str
    url: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    domains: list[str] = Field(default_factory=list)
    summary: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None


class LatestItemsResponse(BaseModel):
    items: list[LatestIngestedItem]
    total: int
