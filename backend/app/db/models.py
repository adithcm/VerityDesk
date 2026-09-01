from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    base_url: Mapped[str | None] = mapped_column(String(2048))
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    access_method: Mapped[str] = mapped_column(String(80))
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_license: Mapped[bool] = mapped_column(Boolean, default=False)
    allows_full_text_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    allows_redistribution: Mapped[bool] = mapped_column(Boolean, default=False)
    robots_policy_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    update_cadence: Mapped[str | None] = mapped_column(String(120))
    reliability_tier: Mapped[str] = mapped_column(String(40), default="standard")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    articles: Mapped[list["Article"]] = relationship(back_populates="source")
    observations: Mapped[list["EconomicObservation"]] = relationship(back_populates="source")
    citations: Mapped[list["Citation"]] = relationship(back_populates="source")


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("ticker", "exchange", name="uq_companies_ticker_exchange"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    ticker: Mapped[str | None] = mapped_column(String(32), index=True)
    exchange: Mapped[str | None] = mapped_column(String(80))
    cik: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    sector: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(2048))
    investor_relations_url: Mapped[str | None] = mapped_column(String(2048))


class Article(TimestampMixin, Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), index=True)
    publisher: Mapped[str | None] = mapped_column(String(255), index=True)
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    summary: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    dedupe_group_id: Mapped[str | None] = mapped_column(String(128), index=True)
    storage_policy: Mapped[str] = mapped_column(String(80), default="metadata_only")

    source: Mapped[Source] = relationship(back_populates="articles")
    citations: Mapped[list["Citation"]] = relationship(back_populates="article")


class EconomicObservation(TimestampMixin, Base):
    __tablename__ = "economic_observations"
    __table_args__ = (
        UniqueConstraint("series_id", "period", "vintage", "region", name="uq_observation_series_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    series_id: Mapped[str] = mapped_column(String(120), index=True)
    series_name: Mapped[str] = mapped_column(String(255))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(80))
    period: Mapped[str] = mapped_column(String(80), index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vintage: Mapped[str | None] = mapped_column(String(80))
    region: Mapped[str | None] = mapped_column(String(160), index=True)

    source: Mapped[Source] = relationship(back_populates="observations")


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    disclaimer_version: Mapped[str] = mapped_column(String(40), default="v1")
    guardrail_status: Mapped[str] = mapped_column(String(80), default="pending")

    citations: Mapped[list["Citation"]] = relationship(back_populates="report")


class Citation(TimestampMixin, Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(500))
    publisher: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supports_claim: Mapped[str] = mapped_column(Text)

    report: Mapped[Report] = relationship(back_populates="citations")
    article: Mapped[Article | None] = relationship(back_populates="citations")
    source: Mapped[Source] = relationship(back_populates="citations")


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    agent_name: Mapped[str] = mapped_column(String(120), index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled_sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    daily_briefing_time: Mapped[str | None] = mapped_column(String(40))
    llm_provider: Mapped[str] = mapped_column(String(80), default="openai")
    api_key_status: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    disclaimer_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
