"""
Export orders to CSV for accounting/reporting.

Usage:
  docker-compose exec backend python -m app.scripts.export_orders \
    --from 2025-01-01 --to 2025-12-31 --output /tmp/orders.csv
"""
import asyncio
import argparse
import csv
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.order import Order


async def export(date_from: str, date_to: str, output: str) -> None:
    from_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
    to_dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.created_at >= from_dt, Order.created_at <= to_dt)
            .order_by(Order.created_at)
        )
        orders = result.scalars().all()

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "customer_id", "status", "payment_status",
                         "subtotal", "shipping_fee", "discount", "total",
                         "items_count", "created_at"])
        for o in orders:
            writer.writerow([
                str(o.id), str(o.customer_id), o.status, o.payment_status,
                float(o.subtotal), float(o.shipping_fee), float(o.discount), float(o.total),
                len(o.items), o.created_at.isoformat(),
            ])

    print(f"✅ Exported {len(orders)} orders to {output}")


def main():
    parser = argparse.ArgumentParser(description="Export Wearify orders to CSV")
    parser.add_argument("--from", dest="date_from", default="2025-01-01")
    parser.add_argument("--to", dest="date_to", default="2025-12-31")
    parser.add_argument("--output", default="/tmp/wearify_orders.csv")
    args = parser.parse_args()
    asyncio.run(export(args.date_from, args.date_to, args.output))


if __name__ == "__main__":
    main()
