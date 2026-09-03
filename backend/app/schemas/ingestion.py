from typing import Literal

from pydantic import BaseModel, Field


IngestionRunMode = Literal["all", "rss", "official_api"]
IngestionRunStatus = Literal["success", "partial_success", "failed", "already_running"]


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
