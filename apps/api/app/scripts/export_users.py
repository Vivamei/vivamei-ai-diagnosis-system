"""用户导出脚本：把 users 解密后导出为 CSV（Excel 可直接打开）。

因为 user.phone 是 AES-GCM 密文，直接导库拿到的是乱码；本脚本在导出时用
DEK 解密后写明文号码到 CSV，并写一条审计日志（谁在何时导了多少条）。

默认只导有效用户（deleted_at 为空）。

用法（在容器内跑，读同一个 .env 连 RDS）：
    python -m app.scripts.export_users --out /export/users.csv
    python -m app.scripts.export_users --days 30 --out /export/x.csv
    python -m app.scripts.export_users --include-deleted --operator 张三 --out /export/x.csv

参数：
    --out               输出文件路径（必填）
    --days N            只导最近 N 天注册的用户（默认全部）
    --include-deleted   连已注销用户（deleted_at 非空）一并导出（默认只导有效用户）
    --operator          操作人标识，写进审计日志（可选）

⚠️ 导出的是敏感个人信息：只导必要范围、文件加密码传递、用完即删。
"""
import argparse
import asyncio
import csv
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.phone_crypto import decrypt_phone

# CSV 表头（顺序即列顺序）
HEADERS = ["用户ID", "昵称", "手机号", "同意版本", "同意时间", "注册时间", "注销时间"]


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _phone_cell(ciphertext: str) -> str:
    """解密并包成 Excel 文本，避免手机号被识别成科学计数法。"""
    try:
        phone = decrypt_phone(ciphertext)
    except Exception:
        logger.warning("一条用户手机号解密失败，已跳过号码")
        return ""
    # ="138..." 让 Excel 按文本处理
    return f'="{phone}"'


async def export(out_path: str, days: int | None, include_deleted: bool, operator: str | None) -> int:
    stmt = select(User).order_by(User.created_at.desc())
    if not include_deleted:
        stmt = stmt.where(User.deleted_at.is_(None))
    if days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = stmt.where(User.created_at >= since)

    async with SessionLocal() as s:
        rows = (await s.execute(stmt)).scalars().all()

        # newline="" 是 csv 模块要求；utf-8-sig 带 BOM，Excel 中文不乱码
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(HEADERS)
            for u in rows:
                w.writerow([
                    u.id,
                    u.nickname or "",
                    _phone_cell(u.phone),
                    u.consent_ver,
                    _fmt_dt(u.consent_at),
                    _fmt_dt(u.created_at),
                    _fmt_dt(u.deleted_at),
                ])

        # 审计：谁在何时导了多少条、什么范围
        s.add(AuditLog(
            actor_id=None,
            action="export_users",
            target_type="user",
            target_id=None,
            meta={
                "count": len(rows),
                "operator": operator,
                "days": days,
                "include_deleted": include_deleted,
                "out": out_path,
            },
        ))
        await s.commit()

    logger.info("导出完成：{} 条 → {}", len(rows), out_path)
    return len(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="导出用户为 CSV（Excel 可打开）")
    p.add_argument("--out", required=True, help="输出文件路径，如 /export/users.csv")
    p.add_argument("--days", type=int, default=None, help="只导最近 N 天注册的用户")
    p.add_argument(
        "--include-deleted",
        action="store_true",
        help="连已注销用户（deleted_at 非空）一并导出，默认只导有效用户",
    )
    p.add_argument("--operator", default=None, help="操作人，写入审计日志")
    args = p.parse_args()

    asyncio.run(export(args.out, args.days, args.include_deleted, args.operator))


if __name__ == "__main__":
    main()
