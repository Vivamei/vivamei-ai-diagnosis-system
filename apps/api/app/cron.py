"""定时任务入口。

启动方式：
    python -m app.cron        # 本地或容器内运行
docker-compose 中以独立 service 启动（不与 api 同进程，避免阻塞）。
"""
import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy import select

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models.photo import Photo


async def cleanup_expired_photos() -> int:
    """软删 expires_at < now 的 photo。

    生产环境需额外删除 OSS 对象（M10 部署阶段补 services/oss.py:delete_object 实现）。
    """
    now = datetime.utcnow()
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(Photo).where(
                    Photo.expires_at < now, Photo.deleted_at.is_(None)
                )
            )
        ).scalars().all()
        for p in rows:
            p.deleted_at = now
            # TODO(prod): await delete_object(p.oss_key)
        await s.commit()
        logger.info("cron: soft-deleted {} expired photos", len(rows))
        return len(rows)


async def main() -> None:
    configure_logging()
    while True:
        try:
            await cleanup_expired_photos()
        except Exception:
            logger.exception("cron iteration failed")
        await asyncio.sleep(3600)  # 每小时一轮


if __name__ == "__main__":
    asyncio.run(main())
