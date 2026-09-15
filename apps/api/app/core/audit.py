from typing import Any

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog


async def write_audit(
    action: str,
    *,
    actor_id: int | None = None,
    actor_ip: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """异步审计日志写入。

    所有"涉敏感数据 / 涉合规判定"动作都应通过本 helper 落 audit_logs 表。
    使用独立 session 避免污染主请求事务。
    """
    async with SessionLocal() as s:
        s.add(
            AuditLog(
                action=action,
                actor_id=actor_id,
                actor_ip=actor_ip,
                target_type=target_type,
                target_id=target_id,
                meta=meta,
            )
        )
        await s.commit()
