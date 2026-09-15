#!/usr/bin/env python
"""留资 CSV 导出工具。

Usage:
    cd apps/api
    poetry run python ../../scripts/export-leads.py \
        --from 2026-06-01 --to 2026-06-30 --out leads.csv
"""
import argparse
import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

# 把 apps/api 加到 sys.path 以便 import app.*
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.booking import Booking  # noqa: E402
from app.services.phone_crypto import decrypt_phone  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    start = datetime.strptime(args.from_, "%Y-%m-%d")
    end = datetime.strptime(args.to, "%Y-%m-%d")

    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(Booking)
                .where(Booking.created_at >= start, Booking.created_at < end)
                .order_by(Booking.created_at)
            )
        ).scalars().all()

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "bookingId", "createdAt", "name", "phone",
            "storeCode", "appointmentAt", "status", "source", "taskId",
        ])
        for r in rows:
            w.writerow([
                r.id,
                r.created_at.isoformat(),
                r.name,
                decrypt_phone(r.phone),
                r.store_code or "",
                r.appointment_at.isoformat() if r.appointment_at else "",
                r.status.value,
                r.source or "",
                r.task_id or "",
            ])
    print(f"exported {len(rows)} rows → {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
