"""管理员数据接口：返回用户列表（含解密手机号明文）。

⚠️ 返回敏感个人信息（PII）。用 X-Admin-Token 头鉴权（见 app/deps/admin.py），
生产务必在 .env 配一个长随机 ADMIN_TOKEN；未配置则接口一律 403。

每次调用写一条 export_users_api 审计日志（谁在哪个 IP、拉了多少条、什么范围）。
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy import select

from app.core.audit import write_audit
from app.deps.admin import require_admin
from app.deps.db import get_db
from app.models.user import User
from app.services.phone_crypto import decrypt_phone

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _fmt_dt(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _phone(ciphertext: str) -> str:
    try:
        return decrypt_phone(ciphertext)
    except Exception:
        logger.warning("一条用户手机号解密失败，已置空")
        return ""


@router.get("/users")
async def list_users(
    actor_ip: str = Depends(require_admin),
    db=Depends(get_db),
    days: int | None = Query(default=None, description="只返回最近 N 天注册的用户"),
    include_deleted: bool = Query(default=False, description="含已注销用户"),
):
    """返回用户列表（默认只含有效用户，手机号为解密明文）。"""
    stmt = select(User).order_by(User.created_at.desc())
    if not include_deleted:
        stmt = stmt.where(User.deleted_at.is_(None))
    if days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = stmt.where(User.created_at >= since)

    rows = (await db.execute(stmt)).scalars().all()

    await write_audit(
        "export_users_api",
        actor_ip=actor_ip,
        target_type="user",
        meta={"count": len(rows), "days": days, "include_deleted": include_deleted},
    )

    return {
        "count": len(rows),
        "users": [
            {
                "id": u.id,
                "nickname": u.nickname,
                "phone": _phone(u.phone),
                "consentVer": u.consent_ver,
                "consentAt": _fmt_dt(u.consent_at),
                "createdAt": _fmt_dt(u.created_at),
                "deletedAt": _fmt_dt(u.deleted_at),
            }
            for u in rows
        ],
    }
