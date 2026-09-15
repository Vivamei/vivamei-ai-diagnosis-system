"""add wechat openid/unionid to users

Revision ID: 008
Revises: 007
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 老用户（短信注册）这两列为 NULL。MySQL 唯一索引允许多行 NULL，故 openid
    # 可以既唯一又对未绑定微信的老用户留空。
    op.add_column("users", sa.Column("wx_openid", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("wx_unionid", sa.String(64), nullable=True))
    op.create_index("ix_users_wx_openid", "users", ["wx_openid"], unique=True)
    op.create_index("ix_users_wx_unionid", "users", ["wx_unionid"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_wx_unionid", table_name="users")
    op.drop_index("ix_users_wx_openid", table_name="users")
    op.drop_column("users", "wx_unionid")
    op.drop_column("users", "wx_openid")
