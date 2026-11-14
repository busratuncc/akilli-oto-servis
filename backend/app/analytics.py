from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import inspection, models, scheduling, schemas


WORKSHOP_TIMEZONE = ZoneInfo("Europe/Istanbul")


def period_bounds(days: int, now: datetime | None = None) -> tuple[datetime, datetime, datetime, datetime]:
    """Return equally long current and previous UTC windows."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    local_now = current.astimezone(WORKSHOP_TIMEZONE)
    local_start = datetime.combine(
        local_now.date() - timedelta(days=days - 1),
        time.min,
        tzinfo=WORKSHOP_TIMEZONE,
    )
    current_start = local_start.astimezone(timezone.utc)
    previous_end = current_start
    previous_start = previous_end - (current - current_start)
    return current_start, current, previous_start, previous_end


def percent_change(current: float | Decimal | int | None, previous: float | Decimal | int | None) -> float | None:
    if current is None or previous is None:
        return None
    current_value = float(current)
    previous_value = float(previous)
    if previous_value == 0:
        return 0.0 if current_value == 0 else None
    return round(((current_value - previous_value) / abs(previous_value)) * 100, 1)


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100, 1)


def local_date(value: datetime) -> date:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(WORKSHOP_TIMEZONE).date()


def _metric(
    current: float | Decimal | int | None,
    previous: float | Decimal | int | None,
    *,
    numerator: int | None = None,
    denominator: int | None = None,
) -> schemas.AnalyticsMetric:
    current_value = None if current is None else float(current)
    previous_value = None if previous is None else float(previous)
    return schemas.AnalyticsMetric(
        current=current_value,
        previous=previous_value,
        change_percent=percent_change(current_value, previous_value),
        numerator=numerator,
        denominator=denominator,
    )


def _in_window(column, start: datetime, end: datetime):
    return column >= start, column < end


def _money_total(db: Session, column, owner_filter, time_column, start: datetime, end: datetime) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(column), Decimal("0"))).where(
            owner_filter,
            *_in_window(time_column, start, end),
        )
    )
    return Decimal(value or 0)


def _completed_rows(db: Session, user_id, start: datetime, end: datetime) -> list[models.WorkOrder]:
    return list(
        db.scalars(
            select(models.WorkOrder)
            .join(models.WorkOrder.vehicle)
            .where(
                models.Vehicle.owner_id == user_id,
                *_in_window(models.WorkOrder.completed_at, start, end),
            )
        ).all()
    )


def _average_turnaround(rows: list[models.WorkOrder]) -> float | None:
    durations = [
        (row.completed_at - row.created_at).total_seconds() / 3600
        for row in rows
        if row.completed_at is not None and row.created_at is not None
    ]
    return round(sum(durations) / len(durations), 1) if durations else None


def _decision_rate(db: Session, user_id, start: datetime, end: datetime) -> tuple[float | None, int, int]:
    rows = db.execute(
        select(models.Estimate.status, func.count())
        .where(
            models.Estimate.owner_id == user_id,
            models.Estimate.status.in_(("approved", "rejected", "converted")),
            *_in_window(models.Estimate.responded_at, start, end),
        )
        .group_by(models.Estimate.status)
    ).all()
    counts = dict(rows)
    approved = counts.get("approved", 0) + counts.get("converted", 0)
    decided = approved + counts.get("rejected", 0)
    return rate(approved, decided), approved, decided


def _no_show_rate(db: Session, user_id, start: datetime, end: datetime) -> tuple[float | None, int, int]:
    rows = db.execute(
        select(models.Appointment.status, func.count())
        .where(
            models.Appointment.owner_id == user_id,
            models.Appointment.status.in_(("completed", "no_show")),
            *_in_window(models.Appointment.scheduled_start, start, end),
        )
        .group_by(models.Appointment.status)
    ).all()
    counts = dict(rows)
    no_shows = counts.get("no_show", 0)
    resolved = no_shows + counts.get("completed", 0)
    return rate(no_shows, resolved), no_shows, resolved


def build_overview(db: Session, user_id, days: int) -> schemas.AnalyticsOverview:
    current_start, current_end, previous_start, previous_end = period_bounds(days)

    current_invoiced = _money_total(
        db,
        models.Invoice.total_amount,
        (models.Invoice.owner_id == user_id) & (models.Invoice.status != "cancelled"),
        models.Invoice.issued_at,
        current_start,
        current_end,
    )
    previous_invoiced = _money_total(
        db,
        models.Invoice.total_amount,
        (models.Invoice.owner_id == user_id) & (models.Invoice.status != "cancelled"),
        models.Invoice.issued_at,
        previous_start,
        previous_end,
    )
    current_collected = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(models.Payment.amount), Decimal("0")))
            .join(models.Payment.invoice)
            .where(
                models.Invoice.owner_id == user_id,
                models.Invoice.status != "cancelled",
                *_in_window(models.Payment.received_at, current_start, current_end),
            )
        )
        or 0
    )
    previous_collected = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(models.Payment.amount), Decimal("0")))
            .join(models.Payment.invoice)
            .where(
                models.Invoice.owner_id == user_id,
                models.Invoice.status != "cancelled",
                *_in_window(models.Payment.received_at, previous_start, previous_end),
            )
        )
        or 0
    )

    current_completed = _completed_rows(db, user_id, current_start, current_end)
    previous_completed = _completed_rows(db, user_id, previous_start, previous_end)
    current_approval, approval_numerator, approval_denominator = _decision_rate(
        db, user_id, current_start, current_end
    )
    previous_approval, _, _ = _decision_rate(db, user_id, previous_start, previous_end)
    current_no_show, no_show_numerator, no_show_denominator = _no_show_rate(
        db, user_id, current_start, current_end
    )
    previous_no_show, _, _ = _no_show_rate(db, user_id, previous_start, previous_end)

    active_work_orders = db.scalar(
        select(func.count())
        .select_from(models.WorkOrder)
        .join(models.WorkOrder.vehicle)
        .where(
            models.Vehicle.owner_id == user_id,
            models.WorkOrder.status.not_in(("completed", "cancelled")),
        )
    ) or 0
    low_stock_parts = db.scalar(
        select(func.count())
        .select_from(models.InventoryPart)
        .where(
            models.InventoryPart.owner_id == user_id,
            models.InventoryPart.active.is_(True),
            models.InventoryPart.stock_quantity <= models.InventoryPart.low_stock_threshold,
        )
    ) or 0

    reminders = db.execute(
        select(models.MaintenanceReminder, models.Vehicle.mileage)
        .join(models.Vehicle, models.MaintenanceReminder.vehicle_id == models.Vehicle.id)
        .where(models.MaintenanceReminder.owner_id == user_id)
    ).all()
    overdue_reminders = sum(
        scheduling.reminder_state(
            status=reminder.status,
            due_date=reminder.due_date,
            due_mileage=reminder.due_mileage,
            current_mileage=mileage,
        ) == "overdue"
        for reminder, mileage in reminders
    )

    completed_inspections = list(
        db.scalars(
            select(models.InspectionReport)
            .options(selectinload(models.InspectionReport.items))
            .where(
                models.InspectionReport.owner_id == user_id,
                models.InspectionReport.status == "completed",
                *_in_window(models.InspectionReport.completed_at, current_start, current_end),
            )
        ).all()
    )
    health_scores = [
        summary["health_score"]
        for report in completed_inspections
        if (summary := inspection.summarize(report.items))["checked_count"] > 0
    ]
    inspection_average_health = (
        round(sum(health_scores) / len(health_scores), 1) if health_scores else None
    )
    unresolved_critical_findings = db.scalar(
        select(func.count())
        .select_from(models.InspectionItem)
        .join(models.InspectionItem.report)
        .where(
            models.InspectionReport.owner_id == user_id,
            models.InspectionItem.condition == "critical",
            models.InspectionItem.resolved.is_(False),
        )
    ) or 0

    status_rows = db.execute(
        select(models.WorkOrder.status, func.count())
        .join(models.WorkOrder.vehicle)
        .where(models.Vehicle.owner_id == user_id)
        .group_by(models.WorkOrder.status)
    ).all()
    status_counts = dict(status_rows)

    funnel_rows = db.execute(
        select(models.Estimate.status, func.count())
        .where(
            models.Estimate.owner_id == user_id,
            *_in_window(models.Estimate.created_at, current_start, current_end),
        )
        .group_by(models.Estimate.status)
    ).all()
    funnel_counts = dict(funnel_rows)

    top_service_rows = db.execute(
        select(models.Appointment.service_type, func.count().label("service_count"))
        .where(
            models.Appointment.owner_id == user_id,
            models.Appointment.status != "cancelled",
            *_in_window(models.Appointment.scheduled_start, current_start, current_end),
        )
        .group_by(models.Appointment.service_type)
        .order_by(func.count().desc(), models.Appointment.service_type)
        .limit(5)
    ).all()

    series_map: dict[date, dict[str, Decimal | int]] = {
        local_date(current_start) + timedelta(days=offset): {
            "invoiced": Decimal("0"),
            "collected": Decimal("0"),
            "completed_orders": 0,
        }
        for offset in range(days)
    }
    invoice_rows = db.execute(
        select(models.Invoice.issued_at, models.Invoice.total_amount).where(
            models.Invoice.owner_id == user_id,
            models.Invoice.status != "cancelled",
            *_in_window(models.Invoice.issued_at, current_start, current_end),
        )
    ).all()
    payment_rows = db.execute(
        select(models.Payment.received_at, models.Payment.amount)
        .join(models.Payment.invoice)
        .where(
            models.Invoice.owner_id == user_id,
            models.Invoice.status != "cancelled",
            *_in_window(models.Payment.received_at, current_start, current_end),
        )
    ).all()
    for issued_at, total in invoice_rows:
        series_map[local_date(issued_at)]["invoiced"] += Decimal(total)
    for received_at, amount in payment_rows:
        series_map[local_date(received_at)]["collected"] += Decimal(amount)
    for order in current_completed:
        if order.completed_at is not None:
            series_map[local_date(order.completed_at)]["completed_orders"] += 1

    series = [
        schemas.AnalyticsSeriesPoint(day=day, **values)
        for day, values in sorted(series_map.items())
    ]
    return schemas.AnalyticsOverview(
        period_days=days,
        period_start=current_start,
        period_end=current_end,
        previous_start=previous_start,
        previous_end=previous_end,
        timezone="Europe/Istanbul",
        generated_at=current_end,
        invoiced=_metric(current_invoiced, previous_invoiced),
        collected=_metric(current_collected, previous_collected),
        completed_orders=_metric(len(current_completed), len(previous_completed)),
        average_turnaround_hours=_metric(
            _average_turnaround(current_completed),
            _average_turnaround(previous_completed),
        ),
        estimate_approval_rate=_metric(
            current_approval,
            previous_approval,
            numerator=approval_numerator,
            denominator=approval_denominator,
        ),
        appointment_no_show_rate=_metric(
            current_no_show,
            previous_no_show,
            numerator=no_show_numerator,
            denominator=no_show_denominator,
        ),
        active_work_orders=active_work_orders,
        low_stock_parts=low_stock_parts,
        overdue_reminders=overdue_reminders,
        inspection_average_health=inspection_average_health,
        unresolved_critical_findings=unresolved_critical_findings,
        series=series,
        work_order_statuses=[
            schemas.AnalyticsCategory(key=key, count=status_counts.get(key, 0))
            for key in ("draft", "inspection", "repairing", "waiting_parts", "completed", "cancelled")
        ],
        estimate_funnel=[
            schemas.AnalyticsCategory(key=key, count=funnel_counts.get(key, 0))
            for key in ("draft", "sent", "approved", "rejected", "expired", "converted")
        ],
        top_services=[
            schemas.AnalyticsCategory(key=service_type, count=count)
            for service_type, count in top_service_rows
        ],
    )
