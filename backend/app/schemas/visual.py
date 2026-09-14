from typing import Literal

from pydantic import BaseModel, Field


VisualModuleId = Literal["daily_read", "housing", "markets", "companies", "macro"]
VisualModuleStatus = Literal[
    "ready",
    "high_signal",
    "watch",
    "quiet",
    "needs_refresh",
    "source_not_connected",
    "no_local_data",
]
VisualTrend = Literal["up", "down", "mixed", "flat", "unknown"]
ChartKind = Literal["bar", "line", "spark"]


class VisualChartPoint(BaseModel):
    label: str
    value: float


class VisualChart(BaseModel):
    kind: ChartKind = "bar"
    points: list[VisualChartPoint] = Field(default_factory=list)


class VisualStat(BaseModel):
    label: str
    value: str
    detail: str | None = None


class VisualSource(BaseModel):
    name: str
    status: str
    retrieved_at: str | None = None
    description: str | None = None


class VisualModule(BaseModel):
    id: VisualModuleId
    title: str
    summary: str
    primary_value: str
    primary_label: str
    status: VisualModuleStatus
    trend: VisualTrend
    updated_at: str | None = None
    chart: VisualChart
    stats: list[VisualStat] = Field(default_factory=list)
    sources: list[VisualSource] = Field(default_factory=list)
    related_report_id: int | None = None
    related_watch_item_ids: list[int] = Field(default_factory=list)
    suggested_prompt: str


class VisualModulesResponse(BaseModel):
    modules: list[VisualModule]
    total: int
    generated_at: str
