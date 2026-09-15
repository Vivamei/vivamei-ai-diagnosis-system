"""create analysis_tasks table

Revision ID: 003
Revises: 002
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_tasks",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("photo_id", sa.BigInteger(), sa.ForeignKey("photos.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "streaming",
                "done",
                "failed",
                "moderated_out",
                name="taskstatus",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("llm_provider", sa.String(length=32), nullable=False),
        sa.Column("llm_request", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_tasks_user", "analysis_tasks", ["user_id"])
    op.create_index("idx_tasks_status_created", "analysis_tasks", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_tasks_status_created", table_name="analysis_tasks")
    op.drop_index("idx_tasks_user", table_name="analysis_tasks")
    op.drop_table("analysis_tasks")
