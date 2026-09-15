import hmac

from fastapi import Header, Request

from app.core.config import settings
from app.core.exceptions import AppError


async def require_admin(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> str:
    """管理员令牌鉴权：请求头 X-Admin-Token 必须与 settings.admin_token 完全一致。

    fail-closed：admin_token 未配置（空）时一律拒绝，避免未配置就把 PII 接口裸奔出去。
    返回调用方 IP，供审计日志记录「谁在哪个 IP 拉的数据」。
    """
    expected = settings.admin_token
    if not expected:
        raise AppError("ADMIN_DISABLED", "admin api disabled", status_code=403)
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise AppError("ADMIN_FORBIDDEN", "invalid admin token", status_code=403)
    return request.client.host if request.client else ""
