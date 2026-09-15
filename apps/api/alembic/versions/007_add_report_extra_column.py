"""add extra json column to reports

Revision ID: 007
Revises: 006
Create Date: 2026-07-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MySQL 不支持给已有数据表加 NOT NULL 的 JSON 列（JSON 不能有 DEFAULT），
    # 故列本身 nullable；ORM 插入时 default=dict 保证新行为 {}，旧行 NULL 由读取端兜底。
    op.add_column(
        "reports",
        sa.Column("extra", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "extra")
