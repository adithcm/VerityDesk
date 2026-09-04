from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.agent import AgentCitation, ConfidenceLevel, GuardrailStatus


ReportType = Literal[
    "daily_briefing",
    "company_research",
    "market_strategy",
    "housing",
    "macro",
]

ReportStatus = Literal["draft", "generated", "failed", "archived"]


class ReportCreateRequest(BaseModel):
    report_type: ReportType
    title: str | None = Field(default=None, max_length=255)
    user_query: str | None = Field(default=None, max_length=4000)
    domains: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    time_window: str | None = None


class ReportResponse(BaseModel):
    id: int
    report_type: ReportType
    status: ReportStatus
    title: str
    summary: str | None = None
    body: str
    domains: list[str]
    tickers: list[str]
    companies: list[str]
    as_of: str | None = None
    confidence: ConfidenceLevel
    disclaimer_version: str
    guardrail_status: GuardrailStatus
    metadata: dict[str, Any]
    citations: list[AgentCitation] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int


class ReportDeleteResponse(BaseModel):
    id: int
    deleted: bool

