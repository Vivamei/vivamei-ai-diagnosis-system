"""create photos table

Revision ID: 002
Revises: 001
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("oss_key", sa.String(length=255), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("mime", sa.String(length=32), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "moderation_status",
            sa.Enum("pending", "passed", "rejected", name="moderationstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("moderation_raw", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_photos_user", "photos", ["user_id"])
    op.create_index("idx_photos_expires", "photos", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_photos_expires", table_name="photos")
    op.drop_index("idx_photos_user", table_name="photos")
    op.drop_table("photos")
