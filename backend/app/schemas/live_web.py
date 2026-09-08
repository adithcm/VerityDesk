from typing import Literal

from pydantic import BaseModel, Field


LiveWebProvider = Literal["tavily"]
LiveWebSearchStatus = Literal["success", "skipped", "failed"]
SourceQuality = Literal["primary", "reputable", "provider", "discovery"]


class LiveWebSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    provider: LiveWebProvider = "tavily"
    max_results: int = Field(default=5, ge=1, le=10)
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)


class LiveWebCitation(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    published_at: str | None = None
    retrieved_at: str
    supports_claim: str
    source_quality: SourceQuality


class LiveWebEvidence(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    published_at: str | None = None
    retrieved_at: str
    excerpt: str
    source_quality: SourceQuality
    relevance_score: float = 0
    citation: LiveWebCitation


class LiveWebSearchResponse(BaseModel):
    provider: LiveWebProvider
    status: LiveWebSearchStatus
    query: str
    results: list[LiveWebEvidence] = Field(default_factory=list)
    message: str
