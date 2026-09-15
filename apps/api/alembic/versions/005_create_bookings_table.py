"""create bookings table

Revision ID: 005
Revises: 004
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "task_id",
            sa.String(length=26),
            sa.ForeignKey("analysis_tasks.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("phone", sa.String(length=255), nullable=False),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("store_code", sa.String(length=32), nullable=True),
        sa.Column("appointment_at", sa.DateTime(), nullable=True),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("new", "contacted", "arrived", "closed", name="bookingstatus"),
            nullable=False,
            server_default="new",
        ),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_bookings_user", "bookings", ["user_id"])
    op.create_index("idx_bookings_status_created", "bookings", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_bookings_status_created", table_name="bookings")
    op.drop_index("idx_bookings_user", table_name="bookings")
    op.drop_table("bookings")
