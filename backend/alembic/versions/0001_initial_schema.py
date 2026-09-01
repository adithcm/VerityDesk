"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("domains", sa.JSON(), nullable=False),
        sa.Column("access_method", sa.String(length=80), nullable=False),
        sa.Column("requires_api_key", sa.Boolean(), nullable=False),
        sa.Column("requires_license", sa.Boolean(), nullable=False),
        sa.Column("allows_full_text_storage", sa.Boolean(), nullable=False),
        sa.Column("allows_redistribution", sa.Boolean(), nullable=False),
        sa.Column("robots_policy_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terms_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("update_cadence", sa.String(length=120), nullable=True),
        sa.Column("reliability_tier", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_sources_name")),
    )
    op.create_index(op.f("ix_sources_name"), "sources", ["name"], unique=False)
    op.create_index(op.f("ix_sources_source_type"), "sources", ["source_type"], unique=False)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=True),
        sa.Column("exchange", sa.String(length=80), nullable=True),
        sa.Column("cik", sa.String(length=32), nullable=True),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("industry", sa.String(length=160), nullable=True),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("investor_relations_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("cik", name=op.f("uq_companies_cik")),
        sa.UniqueConstraint("ticker", "exchange", name="uq_companies_ticker_exchange"),
    )
    op.create_index(op.f("ix_companies_cik"), "companies", ["cik"], unique=False)
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=False)
    op.create_index(op.f("ix_companies_ticker"), "companies", ["ticker"], unique=False)

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("domains", sa.JSON(), nullable=False),
        sa.Column("tickers", sa.JSON(), nullable=False),
        sa.Column("companies", sa.JSON(), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("dedupe_group_id", sa.String(length=128), nullable=True),
        sa.Column("storage_policy", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_articles_source_id_sources")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles")),
        sa.UniqueConstraint("url", name=op.f("uq_articles_url")),
    )
    op.create_index(op.f("ix_articles_canonical_url"), "articles", ["canonical_url"], unique=False)
    op.create_index(op.f("ix_articles_content_hash"), "articles", ["content_hash"], unique=False)
    op.create_index(op.f("ix_articles_dedupe_group_id"), "articles", ["dedupe_group_id"], unique=False)
    op.create_index(op.f("ix_articles_published_at"), "articles", ["published_at"], unique=False)
    op.create_index(op.f("ix_articles_publisher"), "articles", ["publisher"], unique=False)
    op.create_index(op.f("ix_articles_source_id"), "articles", ["source_id"], unique=False)
    op.create_index(op.f("ix_articles_title"), "articles", ["title"], unique=False)

    op.create_table(
        "economic_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("series_id", sa.String(length=120), nullable=False),
        sa.Column("series_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("period", sa.String(length=80), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("vintage", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_economic_observations_source_id_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_economic_observations")),
        sa.UniqueConstraint("series_id", "period", "vintage", "region", name="uq_observation_series_period"),
    )
    op.create_index(op.f("ix_economic_observations_period"), "economic_observations", ["period"], unique=False)
    op.create_index(op.f("ix_economic_observations_region"), "economic_observations", ["region"], unique=False)
    op.create_index(
        op.f("ix_economic_observations_released_at"),
        "economic_observations",
        ["released_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_economic_observations_series_id"),
        "economic_observations",
        ["series_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_economic_observations_source_id"),
        "economic_observations",
        ["source_id"],
        unique=False,
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("domains", sa.JSON(), nullable=False),
        sa.Column("tickers", sa.JSON(), nullable=False),
        sa.Column("companies", sa.JSON(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disclaimer_version", sa.String(length=40), nullable=False),
        sa.Column("guardrail_status", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
    )
    op.create_index(op.f("ix_reports_as_of"), "reports", ["as_of"], unique=False)
    op.create_index(op.f("ix_reports_report_type"), "reports", ["report_type"], unique=False)
    op.create_index(op.f("ix_reports_title"), "reports", ["title"], unique=False)

    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supports_claim", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=op.f("fk_citations_article_id_articles")),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], name=op.f("fk_citations_report_id_reports")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_citations_source_id_sources")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_citations")),
    )
    op.create_index(op.f("ix_citations_article_id"), "citations", ["article_id"], unique=False)
    op.create_index(op.f("ix_citations_report_id"), "citations", ["report_id"], unique=False)
    op.create_index(op.f("ix_citations_source_id"), "citations", ["source_id"], unique=False)

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("agent_name", sa.String(length=120), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
    )
    op.create_index(op.f("ix_agent_runs_agent_name"), "agent_runs", ["agent_name"], unique=False)
    op.create_index(op.f("ix_agent_runs_request_id"), "agent_runs", ["request_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"], unique=False)

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("watchlist_tickers", sa.JSON(), nullable=False),
        sa.Column("preferred_regions", sa.JSON(), nullable=False),
        sa.Column("enabled_sources", sa.JSON(), nullable=False),
        sa.Column("daily_briefing_time", sa.String(length=40), nullable=True),
        sa.Column("llm_provider", sa.String(length=80), nullable=False),
        sa.Column("api_key_status", sa.JSON(), nullable=False),
        sa.Column("disclaimer_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_settings")),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index(op.f("ix_agent_runs_status"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_request_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_agent_name"), table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index(op.f("ix_citations_source_id"), table_name="citations")
    op.drop_index(op.f("ix_citations_report_id"), table_name="citations")
    op.drop_index(op.f("ix_citations_article_id"), table_name="citations")
    op.drop_table("citations")
    op.drop_index(op.f("ix_reports_title"), table_name="reports")
    op.drop_index(op.f("ix_reports_report_type"), table_name="reports")
    op.drop_index(op.f("ix_reports_as_of"), table_name="reports")
    op.drop_table("reports")
    op.drop_index(op.f("ix_economic_observations_source_id"), table_name="economic_observations")
    op.drop_index(op.f("ix_economic_observations_series_id"), table_name="economic_observations")
    op.drop_index(op.f("ix_economic_observations_released_at"), table_name="economic_observations")
    op.drop_index(op.f("ix_economic_observations_region"), table_name="economic_observations")
    op.drop_index(op.f("ix_economic_observations_period"), table_name="economic_observations")
    op.drop_table("economic_observations")
    op.drop_index(op.f("ix_articles_title"), table_name="articles")
    op.drop_index(op.f("ix_articles_source_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_publisher"), table_name="articles")
    op.drop_index(op.f("ix_articles_published_at"), table_name="articles")
    op.drop_index(op.f("ix_articles_dedupe_group_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_content_hash"), table_name="articles")
    op.drop_index(op.f("ix_articles_canonical_url"), table_name="articles")
    op.drop_table("articles")
    op.drop_index(op.f("ix_companies_ticker"), table_name="companies")
    op.drop_index(op.f("ix_companies_name"), table_name="companies")
    op.drop_index(op.f("ix_companies_cik"), table_name="companies")
    op.drop_table("companies")
    op.drop_index(op.f("ix_sources_source_type"), table_name="sources")
    op.drop_index(op.f("ix_sources_name"), table_name="sources")
    op.drop_table("sources")
