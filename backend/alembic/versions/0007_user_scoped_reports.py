"""user scoped reports

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_reports_user_id"), ["user_id"], unique=False)
        batch_op.create_foreign_key("fk_reports_user_id_users", "users", ["user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_constraint("fk_reports_user_id_users", type_="foreignkey")
        batch_op.drop_index(op.f("ix_reports_user_id"))
        batch_op.drop_column("user_id")
