"""预约导出脚本：把 bookings 解密后导出为 CSV（Excel 可直接打开）。

因为 booking.phone 是 AES-GCM 密文，直接导库拿到的是乱码；本脚本在导出时用
DEK 解密后写明文号码到 CSV，并写一条审计日志（谁在何时导了多少条）。

用法（在容器内跑，读同一个 .env 连 RDS）：
    python -m app.scripts.export_bookings --out /export/bookings.csv
    python -m app.scripts.export_bookings --days 7 --status new --out /export/x.csv
    python -m app.scripts.export_bookings --status new,contacted --operator 张三 --out /export/x.csv

参数：
    --out       输出文件路径（必填）
    --days N    只导最近 N 天创建的预约（默认全部）
    --status    只导指定状态，逗号分隔：new,contacted,arrived,closed（默认全部）
    --operator  操作人标识，写进审计日志（可选）

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
from app.models.booking import Booking, BookingStatus
from app.services.phone_crypto import decrypt_phone

# CSV 表头（顺序即列顺序）
HEADERS = ["预约ID", "姓名", "手机号", "预约时间", "门店", "状态", "创建时间", "备注"]

STATUS_LABELS = {
    BookingStatus.new: "新预约",
    BookingStatus.contacted: "已联系",
    BookingStatus.arrived: "到店",
    BookingStatus.closed: "关闭",
}


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _phone_cell(ciphertext: str) -> str:
    """解密并包成 Excel 文本，避免手机号被识别成科学计数法。"""
    try:
        phone = decrypt_phone(ciphertext)
    except Exception:
        logger.warning("一条预约手机号解密失败，已跳过号码")
        return ""
    # ="138..." 让 Excel 按文本处理
    return f'="{phone}"'


def _parse_statuses(raw: str | None) -> list[BookingStatus]:
    if not raw:
        return []
    out: list[BookingStatus] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(BookingStatus(token))
        except ValueError:
            valid = ", ".join(s.value for s in BookingStatus)
            raise SystemExit(f"未知状态 '{token}'，可选：{valid}")
    return out


async def export(out_path: str, days: int | None, statuses: list[BookingStatus], operator: str | None) -> int:
    stmt = select(Booking).order_by(Booking.created_at.desc())
    if days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = stmt.where(Booking.created_at >= since)
    if statuses:
        stmt = stmt.where(Booking.status.in_(statuses))

    async with SessionLocal() as s:
        rows = (await s.execute(stmt)).scalars().all()

        # newline="" 是 csv 模块要求；utf-8-sig 带 BOM，Excel 中文不乱码
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(HEADERS)
            for b in rows:
                w.writerow([
                    b.id,
                    b.name,
                    _phone_cell(b.phone),
                    _fmt_dt(b.appointment_at),
                    b.store_code or "",
                    STATUS_LABELS.get(b.status, b.status.value),
                    _fmt_dt(b.created_at),
                    b.remark or "",
                ])

        # 审计：谁在何时导了多少条、什么范围
        s.add(AuditLog(
            actor_id=None,
            action="export_bookings",
            target_type="booking",
            target_id=None,
            meta={
                "count": len(rows),
                "operator": operator,
                "days": days,
                "statuses": [st.value for st in statuses] or "all",
                "out": out_path,
            },
        ))
        await s.commit()

    logger.info("导出完成：{} 条 → {}", len(rows), out_path)
    return len(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="导出预约为 CSV（Excel 可打开）")
    p.add_argument("--out", required=True, help="输出文件路径，如 /export/bookings.csv")
    p.add_argument("--days", type=int, default=None, help="只导最近 N 天创建的预约")
    p.add_argument("--status", default=None, help="状态过滤，逗号分隔：new,contacted,arrived,closed")
    p.add_argument("--operator", default=None, help="操作人，写入审计日志")
    args = p.parse_args()

    statuses = _parse_statuses(args.status)
    asyncio.run(export(args.out, args.days, statuses, args.operator))


if __name__ == "__main__":
    main()
