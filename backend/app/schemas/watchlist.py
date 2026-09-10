from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


WatchCategory = Literal["market", "company", "housing", "macro", "world", "custom"]
WatchStatus = Literal["watching", "alert", "quiet", "paused"]
WatchPriority = Literal["low", "normal", "high"]


class WatchItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    category: WatchCategory = "custom"
    query: str = Field(min_length=3, max_length=1000)
    priority: WatchPriority = "normal"
    enabled: bool = True


class WatchItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    category: WatchCategory | None = None
    query: str | None = Field(default=None, min_length=3, max_length=1000)
    priority: WatchPriority | None = None
    enabled: bool | None = None


class WatchAlertResponse(BaseModel):
    id: int
    watch_item_id: int
    report_id: int | None = None
    title: str
    message: str
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class WatchItemResponse(BaseModel):
    id: int
    title: str
    category: str
    query: str
    status: str
    priority: str
    enabled: bool
    last_checked_at: datetime | None = None
    last_matched_at: datetime | None = None
    last_summary: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    alerts: list[WatchAlertResponse] = Field(default_factory=list)


class WatchItemListResponse(BaseModel):
    items: list[WatchItemResponse]
    total: int


class WatchEvaluationResponse(BaseModel):
    checked: int
    triggered: int
    alerts: list[WatchAlertResponse]
