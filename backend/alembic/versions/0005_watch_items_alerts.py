"""watch items alerts

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watch_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="custom"),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="watching"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_summary", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watch_items_category"), "watch_items", ["category"], unique=False)
    op.create_index(op.f("ix_watch_items_enabled"), "watch_items", ["enabled"], unique=False)
    op.create_index(op.f("ix_watch_items_status"), "watch_items", ["status"], unique=False)
    op.create_index(op.f("ix_watch_items_title"), "watch_items", ["title"], unique=False)

    op.create_table(
        "watch_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("watch_item_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="new"),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.ForeignKeyConstraint(["watch_item_id"], ["watch_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watch_alerts_report_id"), "watch_alerts", ["report_id"], unique=False)
    op.create_index(op.f("ix_watch_alerts_status"), "watch_alerts", ["status"], unique=False)
    op.create_index(op.f("ix_watch_alerts_title"), "watch_alerts", ["title"], unique=False)
    op.create_index(op.f("ix_watch_alerts_triggered_at"), "watch_alerts", ["triggered_at"], unique=False)
    op.create_index(op.f("ix_watch_alerts_watch_item_id"), "watch_alerts", ["watch_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_watch_alerts_watch_item_id"), table_name="watch_alerts")
    op.drop_index(op.f("ix_watch_alerts_triggered_at"), table_name="watch_alerts")
    op.drop_index(op.f("ix_watch_alerts_title"), table_name="watch_alerts")
    op.drop_index(op.f("ix_watch_alerts_status"), table_name="watch_alerts")
    op.drop_index(op.f("ix_watch_alerts_report_id"), table_name="watch_alerts")
    op.drop_table("watch_alerts")
    op.drop_index(op.f("ix_watch_items_title"), table_name="watch_items")
    op.drop_index(op.f("ix_watch_items_status"), table_name="watch_items")
    op.drop_index(op.f("ix_watch_items_enabled"), table_name="watch_items")
    op.drop_index(op.f("ix_watch_items_category"), table_name="watch_items")
    op.drop_table("watch_items")
