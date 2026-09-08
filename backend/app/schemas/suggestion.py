from typing import Literal

from pydantic import BaseModel, Field


SuggestionKind = Literal["question", "report", "evidence_gap"]
SuggestionAction = Literal[
    "run_agent_query",
    "generate_daily_briefing",
    "generate_company_research",
    "generate_market_strategy",
    "generate_housing_report",
    "generate_macro_report",
    "review_sources",
]


class ProactiveSuggestion(BaseModel):
    id: str
    kind: SuggestionKind
    title: str
    prompt: str
    action: SuggestionAction
    priority: int = Field(ge=1, le=5)
    domains: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    guardrail_note: str


class ProactiveSuggestionsResponse(BaseModel):
    suggestions: list[ProactiveSuggestion]
    total: int
    generated_at: str
