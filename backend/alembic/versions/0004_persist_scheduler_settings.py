"""persist scheduler settings

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("daily_schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user_settings", sa.Column("daily_schedule_timezone", sa.String(length=80), nullable=False, server_default="local"))
    op.add_column("user_settings", sa.Column("daily_schedule_mode", sa.String(length=40), nullable=False, server_default="all"))
    op.add_column("user_settings", sa.Column("daily_report_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user_settings", sa.Column("daily_last_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_settings", sa.Column("daily_next_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_settings", sa.Column("daily_last_status", sa.String(length=80), nullable=True))
    op.add_column("user_settings", sa.Column("daily_last_message", sa.Text(), nullable=True))
    op.add_column("user_settings", sa.Column("daily_last_report_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_settings", "daily_last_report_id")
    op.drop_column("user_settings", "daily_last_message")
    op.drop_column("user_settings", "daily_last_status")
    op.drop_column("user_settings", "daily_next_run_at")
    op.drop_column("user_settings", "daily_last_run_at")
    op.drop_column("user_settings", "daily_report_enabled")
    op.drop_column("user_settings", "daily_schedule_mode")
    op.drop_column("user_settings", "daily_schedule_timezone")
    op.drop_column("user_settings", "daily_schedule_enabled")
