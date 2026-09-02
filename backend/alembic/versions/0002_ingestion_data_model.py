"""ingestion data model

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("run_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_seen", sa.Integer(), nullable=False),
        sa.Column("items_inserted", sa.Integer(), nullable=False),
        sa.Column("items_updated", sa.Integer(), nullable=False),
        sa.Column("items_skipped", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_ingestion_runs_source_id_sources")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_runs")),
    )
    op.create_index(op.f("ix_ingestion_runs_completed_at"), "ingestion_runs", ["completed_at"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_run_type"), "ingestion_runs", ["run_type"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_source_id"), "ingestion_runs", ["source_id"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_source_key"), "ingestion_runs", ["source_key"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_started_at"), "ingestion_runs", ["started_at"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_status"), "ingestion_runs", ["status"], unique=False)

    op.create_table(
        "source_health",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_item_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_item_title", sa.String(length=500), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("freshness_window_hours", sa.Integer(), nullable=False),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_source_health_source_id_sources")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_health")),
        sa.UniqueConstraint("source_key", name=op.f("uq_source_health_source_key")),
    )
    op.create_index(op.f("ix_source_health_last_attempt_at"), "source_health", ["last_attempt_at"], unique=False)
    op.create_index(op.f("ix_source_health_last_success_at"), "source_health", ["last_success_at"], unique=False)
    op.create_index(
        op.f("ix_source_health_latest_item_published_at"),
        "source_health",
        ["latest_item_published_at"],
        unique=False,
    )
    op.create_index(op.f("ix_source_health_source_id"), "source_health", ["source_id"], unique=False)
    op.create_index(op.f("ix_source_health_source_key"), "source_health", ["source_key"], unique=False)
    op.create_index(op.f("ix_source_health_stale_after"), "source_health", ["stale_after"], unique=False)
    op.create_index(op.f("ix_source_health_status"), "source_health", ["status"], unique=False)

    op.create_table(
        "retrieved_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("storage_policy", sa.String(length=80), nullable=False),
        sa.Column("raw_content_path", sa.String(length=2048), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("response_headers", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=op.f("fk_retrieved_snapshots_article_id_articles")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_retrieved_snapshots_source_id_sources")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retrieved_snapshots")),
    )
    op.create_index(op.f("ix_retrieved_snapshots_article_id"), "retrieved_snapshots", ["article_id"], unique=False)
    op.create_index(op.f("ix_retrieved_snapshots_content_hash"), "retrieved_snapshots", ["content_hash"], unique=False)
    op.create_index(op.f("ix_retrieved_snapshots_retrieved_at"), "retrieved_snapshots", ["retrieved_at"], unique=False)
    op.create_index(op.f("ix_retrieved_snapshots_source_id"), "retrieved_snapshots", ["source_id"], unique=False)
    op.create_index(op.f("ix_retrieved_snapshots_source_key"), "retrieved_snapshots", ["source_key"], unique=False)
    op.create_index(op.f("ix_retrieved_snapshots_url"), "retrieved_snapshots", ["url"], unique=False)

    op.create_table(
        "external_ids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=op.f("fk_external_ids_article_id_articles")),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["economic_observations.id"],
            name=op.f("fk_external_ids_observation_id_economic_observations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_ids")),
        sa.UniqueConstraint("source_key", "external_id", "entity_type", name="uq_external_ids_source_entity"),
    )
    op.create_index(op.f("ix_external_ids_article_id"), "external_ids", ["article_id"], unique=False)
    op.create_index(op.f("ix_external_ids_entity_type"), "external_ids", ["entity_type"], unique=False)
    op.create_index(op.f("ix_external_ids_external_id"), "external_ids", ["external_id"], unique=False)
    op.create_index(op.f("ix_external_ids_observation_id"), "external_ids", ["observation_id"], unique=False)
    op.create_index(op.f("ix_external_ids_source_key"), "external_ids", ["source_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_external_ids_source_key"), table_name="external_ids")
    op.drop_index(op.f("ix_external_ids_observation_id"), table_name="external_ids")
    op.drop_index(op.f("ix_external_ids_external_id"), table_name="external_ids")
    op.drop_index(op.f("ix_external_ids_entity_type"), table_name="external_ids")
    op.drop_index(op.f("ix_external_ids_article_id"), table_name="external_ids")
    op.drop_table("external_ids")
    op.drop_index(op.f("ix_retrieved_snapshots_url"), table_name="retrieved_snapshots")
    op.drop_index(op.f("ix_retrieved_snapshots_source_key"), table_name="retrieved_snapshots")
    op.drop_index(op.f("ix_retrieved_snapshots_source_id"), table_name="retrieved_snapshots")
    op.drop_index(op.f("ix_retrieved_snapshots_retrieved_at"), table_name="retrieved_snapshots")
    op.drop_index(op.f("ix_retrieved_snapshots_content_hash"), table_name="retrieved_snapshots")
    op.drop_index(op.f("ix_retrieved_snapshots_article_id"), table_name="retrieved_snapshots")
    op.drop_table("retrieved_snapshots")
    op.drop_index(op.f("ix_source_health_status"), table_name="source_health")
    op.drop_index(op.f("ix_source_health_stale_after"), table_name="source_health")
    op.drop_index(op.f("ix_source_health_source_key"), table_name="source_health")
    op.drop_index(op.f("ix_source_health_source_id"), table_name="source_health")
    op.drop_index(op.f("ix_source_health_latest_item_published_at"), table_name="source_health")
    op.drop_index(op.f("ix_source_health_last_success_at"), table_name="source_health")
    op.drop_index(op.f("ix_source_health_last_attempt_at"), table_name="source_health")
    op.drop_table("source_health")
    op.drop_index(op.f("ix_ingestion_runs_status"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_started_at"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_source_key"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_source_id"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_run_type"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_completed_at"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
