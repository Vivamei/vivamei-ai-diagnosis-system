import time
from typing import Any

from jose import jwt

from app.core.config import settings

ALG = "HS256"


def _issue(user_id: int, ttl: int, typ: str) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + ttl, "type": typ}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALG)


def issue_access_token(user_id: int, ttl_seconds: int | None = None) -> str:
    return _issue(user_id, ttl_seconds or settings.jwt_access_ttl_seconds, "access")


def issue_refresh_token(user_id: int) -> str:
    return _issue(user_id, settings.jwt_refresh_ttl_seconds, "refresh")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALG])


def issue_wx_bind_token(openid: str, unionid: str | None) -> str:
    """微信登录中间态令牌：已拿到 openid、还差手机号时下发，换手机号时原样回传。

    不是登录凭证（type=wxbind，get_current_user 只认 access），仅用于把 openid
    寄存在客户端，避免让客户端自报 openid 而被伪造。
    """
    now = int(time.time())
    payload = {
        "openid": openid,
        "unionid": unionid,
        "iat": now,
        "exp": now + settings.wx_bind_ttl_seconds,
        "type": "wxbind",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALG)
