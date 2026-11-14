from datetime import datetime, timezone
from decimal import Decimal

from app import analytics


def test_period_bounds_are_time_aligned_in_istanbul():
    now = datetime(2026, 11, 14, 12, 30, tzinfo=timezone.utc)

    current_start, current_end, previous_start, previous_end = analytics.period_bounds(7, now)

    assert current_start == datetime(2026, 11, 7, 21, 0, tzinfo=timezone.utc)
    assert current_end == now
    assert previous_end == current_start
    assert previous_end - previous_start == current_end - current_start


def test_percent_change_preserves_zero_and_missing_baselines():
    assert analytics.percent_change(Decimal("150"), Decimal("100")) == 50.0
    assert analytics.percent_change(0, 0) == 0.0
    assert analytics.percent_change(10, 0) is None
    assert analytics.percent_change(None, 10) is None


def test_rate_distinguishes_no_observations_from_zero_percent():
    assert analytics.rate(0, 0) is None
    assert analytics.rate(0, 4) == 0.0
    assert analytics.rate(1, 4) == 25.0
