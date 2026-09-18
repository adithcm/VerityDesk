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
    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(back_populates="source")
    snapshots: Mapped[list["RetrievedSnapshot"]] = relationship(back_populates="source")
    health: Mapped["SourceHealth | None"] = relationship(back_populates="source")


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
    snapshots: Mapped[list["RetrievedSnapshot"]] = relationship(back_populates="article")
    external_ids: Mapped[list["ExternalID"]] = relationship(back_populates="article")


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
    external_ids: Mapped[list["ExternalID"]] = relationship(back_populates="observation")


class IngestionRun(TimestampMixin, Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(120), index=True)
    run_type: Mapped[str] = mapped_column(String(80), default="manual", index=True)
    status: Mapped[str] = mapped_column(String(80), default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    items_seen: Mapped[int] = mapped_column(default=0)
    items_inserted: Mapped[int] = mapped_column(default=0)
    items_updated: Mapped[int] = mapped_column(default=0)
    items_skipped: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    run_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    source: Mapped[Source | None] = relationship(back_populates="ingestion_runs")


class SourceHealth(TimestampMixin, Base):
    __tablename__ = "source_health"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(80), default="not_configured", index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    latest_item_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    latest_item_title: Mapped[str | None] = mapped_column(String(500))
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    freshness_window_hours: Mapped[int] = mapped_column(default=24)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    health_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    source: Mapped[Source | None] = relationship(back_populates="health")


class RetrievedSnapshot(TimestampMixin, Base):
    __tablename__ = "retrieved_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(120), index=True)
    url: Mapped[str] = mapped_column(String(2048), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    storage_policy: Mapped[str] = mapped_column(String(80), default="metadata_only")
    raw_content_path: Mapped[str | None] = mapped_column(String(2048))
    excerpt: Mapped[str | None] = mapped_column(Text)
    response_headers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    article: Mapped[Article | None] = relationship(back_populates="snapshots")
    source: Mapped[Source | None] = relationship(back_populates="snapshots")


class ExternalID(TimestampMixin, Base):
    __tablename__ = "external_ids"
    __table_args__ = (
        UniqueConstraint("source_key", "external_id", "entity_type", name="uq_external_ids_source_entity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(120), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"), index=True)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("economic_observations.id"), index=True)
    id_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    article: Mapped[Article | None] = relationship(back_populates="external_ids")
    observation: Mapped[EconomicObservation | None] = relationship(back_populates="external_ids")


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(80), default="draft", index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[str] = mapped_column(String(40), default="low")
    disclaimer_version: Mapped[str] = mapped_column(String(40), default="v1")
    guardrail_status: Mapped[str] = mapped_column(String(80), default="pending")
    report_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    citations: Mapped[list["Citation"]] = relationship(back_populates="report", cascade="all, delete-orphan")


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


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    settings: Mapped["UserSettings | None"] = relationship(back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    watchlist_tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled_sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    daily_briefing_time: Mapped[str | None] = mapped_column(String(40))
    daily_schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_schedule_timezone: Mapped[str] = mapped_column(String(80), default="local")
    daily_schedule_mode: Mapped[str] = mapped_column(String(40), default="all")
    daily_report_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    daily_next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    daily_last_status: Mapped[str | None] = mapped_column(String(80))
    daily_last_message: Mapped[str | None] = mapped_column(Text)
    daily_last_report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"))
    llm_provider: Mapped[str] = mapped_column(String(80), default="openai")
    api_key_status: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    disclaimer_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User | None] = relationship(back_populates="settings")


class WatchItem(TimestampMixin, Base):
    __tablename__ = "watch_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(80), default="custom", index=True)
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="watching", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_summary: Mapped[str | None] = mapped_column(Text)
    trigger_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    alerts: Mapped[list["WatchAlert"]] = relationship(back_populates="watch_item", cascade="all, delete-orphan")


class WatchAlert(TimestampMixin, Base):
    __tablename__ = "watch_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    watch_item_id: Mapped[int] = mapped_column(ForeignKey("watch_items.id"), index=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="new", index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    alert_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    watch_item: Mapped[WatchItem] = relationship(back_populates="alerts")
    report: Mapped[Report | None] = relationship()
