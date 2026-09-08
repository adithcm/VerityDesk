from typing import Any, Literal

from pydantic import BaseModel, Field


AgentIntent = Literal[
    "daily_briefing",
    "company_research",
    "market_research",
    "housing_macro_research",
    "general_research",
]

ClaimType = Literal["fact", "interpretation", "forecast", "risk", "scenario"]
ConfidenceLevel = Literal["low", "medium", "high"]
SafetyLevel = Literal["standard", "investment_research"]
GuardrailStatus = Literal["passed", "needs_revision", "blocked"]


class AgentQueryRequest(BaseModel):
    user_query: str = Field(min_length=1, max_length=4000)
    intent: AgentIntent = "general_research"
    domains: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    time_window: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    safety_level: SafetyLevel = "investment_research"


class AgentClaim(BaseModel):
    claim: str
    claim_type: ClaimType
    source_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    as_of: str | None = None


class AgentCitation(BaseModel):
    source_id: str | None = None
    title: str
    url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    supports_claim: str


class AgentContext(BaseModel):
    request_id: str
    user_query: str
    intent: AgentIntent
    domains: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    time_window: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    safety_level: SafetyLevel = "investment_research"
    evidence_packet: dict[str, Any] | None = None


class AgentResult(BaseModel):
    agent_name: str
    summary: str
    claims: list[AgentClaim] = Field(default_factory=list)
    citations: list[AgentCitation] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    risks: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class GuardrailCheck(BaseModel):
    status: GuardrailStatus
    disclaimer: str
    issues: list[str] = Field(default_factory=list)
    banned_phrases_found: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    rewritten_text: str | None = None


class AgentQueryResponse(BaseModel):
    request_id: str
    summary: str
    agents_ran: list[str]
    claims: list[AgentClaim]
    citations: list[AgentCitation]
    confidence: ConfidenceLevel
    risks: list[str]
    follow_up_questions: list[str]
    guardrail: GuardrailCheck
    requires_guardrail_review: bool


class AgentRunRecord(BaseModel):
    id: int
    request_id: str
    agent_name: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class AgentRunHistoryResponse(BaseModel):
    runs: list[AgentRunRecord]
    total: int
