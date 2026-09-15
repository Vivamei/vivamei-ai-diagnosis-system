from dataclasses import dataclass

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy import select

from app.core.exceptions import AppError
from app.core.security import decode_token
from app.deps.db import get_db
from app.deps.redis import get_redis
from app.models.user import User


@dataclass
class CurrentUser:
    id: int
    nickname: str | None


async def get_current_user(
    authorization: str | None = Header(default=None),
    db=Depends(get_db),
    r=Depends(get_redis),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("AUTH_REQUIRED", "missing token", status_code=401)
    token = authorization.split(" ", 1)[1]
    try:
        claims = decode_token(token)
    except JWTError:
        raise AppError("AUTH_INVALID_TOKEN", "invalid token", status_code=401)
    if claims.get("type") != "access":
        raise AppError("AUTH_INVALID_TOKEN", "wrong token type", status_code=401)
    if await r.exists(f"jwt:blacklist:{token}"):
        raise AppError("AUTH_INVALID_TOKEN", "token revoked", status_code=401)
    uid = int(claims["sub"])
    user = (
        await db.execute(
            select(User).where(User.id == uid, User.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not user:
        raise AppError("AUTH_INVALID_TOKEN", "user not found", status_code=401)
    return CurrentUser(id=user.id, nickname=user.nickname)
