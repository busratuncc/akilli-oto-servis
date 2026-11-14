from datetime import date, datetime, timezone

import pytest

from app import scheduling


def test_normalizes_valid_interval_to_utc():
    start = datetime.fromisoformat("2026-11-14T10:00:00+03:00")
    end = datetime.fromisoformat("2026-11-14T11:30:00+03:00")

    normalized_start, normalized_end = scheduling.normalize_interval(start, end)

    assert normalized_start == datetime(2026, 11, 14, 7, 0, tzinfo=timezone.utc)
    assert normalized_end == datetime(2026, 11, 14, 8, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 11, 14, 10), datetime(2026, 11, 14, 11)),
        (
            datetime.fromisoformat("2026-11-14T12:00:00+03:00"),
            datetime.fromisoformat("2026-11-14T11:00:00+03:00"),
        ),
        (
            datetime.fromisoformat("2026-11-14T10:00:00+03:00"),
            datetime.fromisoformat("2026-11-15T11:00:01+03:00"),
        ),
    ],
)
def test_rejects_invalid_intervals(start, end):
    with pytest.raises(ValueError):
        scheduling.normalize_interval(start, end)


def test_local_day_bounds_use_istanbul_timezone():
    start, end = scheduling.local_day_bounds(date(2026, 11, 14))

    assert start == datetime(2026, 11, 13, 21, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 14, 21, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("due_date", "due_mileage", "mileage", "expected"),
    [
        (date(2026, 11, 13), None, None, "overdue"),
        (None, 50_000, 50_100, "overdue"),
        (date(2026, 11, 20), None, None, "due_soon"),
        (None, 50_000, 49_600, "due_soon"),
        (date(2026, 12, 1), 60_000, 50_000, "upcoming"),
    ],
)
def test_calculates_pending_reminder_state(due_date, due_mileage, mileage, expected):
    assert scheduling.reminder_state(
        status="pending",
        due_date=due_date,
        due_mileage=due_mileage,
        current_mileage=mileage,
        today=date(2026, 11, 14),
    ) == expected


def test_terminal_reminder_status_has_priority():
    assert scheduling.reminder_state(
        status="completed",
        due_date=date(2020, 1, 1),
        due_mileage=1,
        current_mileage=99_999,
        today=date(2026, 11, 14),
    ) == "completed"
