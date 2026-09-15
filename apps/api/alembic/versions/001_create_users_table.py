"""create users table

Revision ID: 001
Revises:
Create Date: 2026-06-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("phone", sa.String(length=255), nullable=False),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("nickname", sa.String(length=64), nullable=True),
        sa.Column("consent_at", sa.DateTime(), nullable=False),
        sa.Column("consent_ver", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("uk_phone_hash", "users", ["phone_hash"], unique=True)
    op.create_index("idx_users_created", "users", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_users_created", table_name="users")
    op.drop_index("uk_phone_hash", table_name="users")
    op.drop_table("users")
