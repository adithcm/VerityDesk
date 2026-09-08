from typing import Literal

from pydantic import BaseModel, Field


ResearchWorkflowStepType = Literal[
    "query_understanding",
    "research_planning",
    "live_web_research",
    "direct_api_lookup",
    "local_evidence_lookup",
    "evidence_fusion",
    "specialist_analysis",
    "answer_synthesis",
    "citation_guardrail",
]

ResearchWorkflowStepStatus = Literal["planned", "running", "complete", "skipped", "failed"]
RetrievalChannel = Literal["live_web", "direct_api", "local_cache"]
AnswerStyle = Literal["brief", "standard", "deep_dive"]


class ResearchWorkflowStep(BaseModel):
    step_id: str
    step_type: ResearchWorkflowStepType
    label: str
    status: ResearchWorkflowStepStatus = "planned"
    depends_on: list[str] = Field(default_factory=list)
    hidden_from_primary_ui: bool = True


class EvidenceNeed(BaseModel):
    channel: RetrievalChannel
    purpose: str
    source_ids: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    required: bool = True


class ResearchWorkflowPlan(BaseModel):
    request_id: str
    user_query: str
    intent: str
    domains: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    time_window: str | None = None
    answer_style: AnswerStyle = "standard"
    retrieval_priority: list[RetrievalChannel] = Field(default_factory=list)
    evidence_needs: list[EvidenceNeed] = Field(default_factory=list)
    specialist_agents: list[str] = Field(default_factory=list)
    steps: list[ResearchWorkflowStep] = Field(default_factory=list)
    manual_requirements: list[str] = Field(default_factory=list)
