from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import models, services
from app.database import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        query = select(models.WorkOrder).options(selectinload(models.WorkOrder.dtc_codes))
        work_orders = list(db.scalars(query).unique().all())
        for index, work_order in enumerate(work_orders, start=1):
            provider = services.refresh_work_order_embedding(work_order)
            print(f"[{index}/{len(work_orders)}] {work_order.id} -> {provider}")
        db.commit()
        print(f"{len(work_orders)} iş emrinin embedding alanı güncellendi.")


if __name__ == "__main__":
    main()
