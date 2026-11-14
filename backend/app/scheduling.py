from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo


WORKSHOP_TIMEZONE = ZoneInfo("Europe/Istanbul")
ReminderState = Literal["overdue", "due_soon", "upcoming", "completed", "dismissed"]


def normalize_interval(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Validate an appointment interval and normalize it to UTC."""
    if start.tzinfo is None or start.utcoffset() is None or end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("Randevu saatleri zaman dilimi bilgisi içermelidir")
    normalized_start = start.astimezone(timezone.utc)
    normalized_end = end.astimezone(timezone.utc)
    if normalized_end <= normalized_start:
        raise ValueError("Randevu bitiş saati başlangıç saatinden sonra olmalıdır")
    if normalized_end - normalized_start > timedelta(hours=24):
        raise ValueError("Tek bir randevu 24 saatten uzun olamaz")
    return normalized_start, normalized_end


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=WORKSHOP_TIMEZONE)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def workshop_today(now: datetime | None = None) -> date:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(WORKSHOP_TIMEZONE).date()


def reminder_state(
    *,
    status: str,
    due_date: date | None,
    due_mileage: int | None,
    current_mileage: int | None,
    today: date | None = None,
) -> ReminderState:
    if status == "completed":
        return "completed"
    if status == "dismissed":
        return "dismissed"

    reference_date = today or workshop_today()
    overdue_by_date = due_date is not None and due_date < reference_date
    overdue_by_mileage = (
        due_mileage is not None
        and current_mileage is not None
        and current_mileage >= due_mileage
    )
    if overdue_by_date or overdue_by_mileage:
        return "overdue"

    due_soon_by_date = due_date is not None and due_date <= reference_date + timedelta(days=7)
    due_soon_by_mileage = (
        due_mileage is not None
        and current_mileage is not None
        and current_mileage + 500 >= due_mileage
    )
    if due_soon_by_date or due_soon_by_mileage:
        return "due_soon"
    return "upcoming"
