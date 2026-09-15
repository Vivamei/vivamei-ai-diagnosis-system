"""create reports table

Revision ID: 004
Revises: 003
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=26),
            sa.ForeignKey("analysis_tasks.id"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=8), nullable=False, server_default="v1"),
        sa.Column("stype", sa.JSON(), nullable=False),
        sa.Column("style", sa.JSON(), nullable=False),
        sa.Column("subzone", sa.JSON(), nullable=False),
        sa.Column("struct_", sa.JSON(), nullable=False),
        sa.Column("radar_scores", sa.JSON(), nullable=False),
        sa.Column("optimization", sa.Text(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column(
            "moderation_status",
            sa.Enum("pending", "passed", "rejected", name="reportmoderationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uk_reports_task", "reports", ["task_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uk_reports_task", table_name="reports")
    op.drop_table("reports")
