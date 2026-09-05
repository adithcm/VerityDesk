"""report contract fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("status", sa.String(length=80), nullable=False, server_default="draft"))
    op.add_column("reports", sa.Column("confidence", sa.String(length=40), nullable=False, server_default="low"))
    op.add_column("reports", sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_index(op.f("ix_reports_status"), "reports", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_status"), table_name="reports")
    op.drop_column("reports", "metadata")
    op.drop_column("reports", "confidence")
    op.drop_column("reports", "status")
