from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # AES-GCM ciphertext (base64); 加密存储，不可直接查
    phone: Mapped[str] = mapped_column(String(255), nullable=False)
    # HMAC-SHA256(phone)，建立唯一索引用于按手机号查找
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 微信小程序 openid / unionid。短信注册的老用户为空，微信登录时按手机号回填绑定。
    wx_openid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    wx_unionid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consent_ver: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
