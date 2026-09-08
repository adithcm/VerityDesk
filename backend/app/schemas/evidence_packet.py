from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agent import AgentCitation


EvidencePacketSourceKind = Literal["live_web", "direct_api", "local_cache", "saved_report"]
EvidencePacketStatus = Literal["success", "skipped", "failed"]
EvidencePacketQuality = Literal["primary", "reputable", "provider", "discovery", "internal"]


class EvidenceRetrievalStatus(BaseModel):
    channel: EvidencePacketSourceKind
    status: EvidencePacketStatus
    message: str
    query: str | None = None


class EvidencePacketItem(BaseModel):
    source_kind: EvidencePacketSourceKind
    source_id: str | None = None
    source_name: str | None = None
    title: str
    url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    scope: str | None = None
    summary: str
    source_quality: EvidencePacketQuality = "discovery"
    relevance_score: float = 0
    rank_score: float = 0
    citation: AgentCitation | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class EvidencePacket(BaseModel):
    request_id: str
    query: str
    items: list[EvidencePacketItem] = Field(default_factory=list)
    citations: list[AgentCitation] = Field(default_factory=list)
    retrieval_statuses: list[EvidenceRetrievalStatus] = Field(default_factory=list)

