"""Unit tests for the scheduling math in common/periodicTask.py.

These pin the `_next_delay` callable that each PeriodicTask factory builds.
Frozen `datetime.now()` keeps them deterministic. The asyncio loop itself
is not exercised — that's framework code.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from common.periodicTask import PeriodicTask


# --- PeriodicTask.every (clock-aligned interval) ---


def test_every_on_boundary_returns_full_interval():
    """When the current time is exactly on a boundary, the next boundary is
    one full interval away — we don't fire on the current moment."""
    task = PeriodicTask.every(60, _noop)
    on_boundary = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = on_boundary
        assert task._next_delay() == pytest.approx(60.0)


def test_every_partway_through():
    task = PeriodicTask.every(60, _noop)
    halfway = datetime(2024, 1, 1, 12, 0, 30)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = halfway
        assert task._next_delay() == pytest.approx(30.0)


def test_every_quarter_hour():
    """every(900) should align to :00, :15, :30, :45."""
    task = PeriodicTask.every(900, _noop)
    seven_minutes_thirty_seconds_in = datetime(2024, 1, 1, 12, 7, 30)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = seven_minutes_thirty_seconds_in
        # Next boundary is 12:15:00 — 7m30s away
        assert task._next_delay() == pytest.approx(450.0)


def test_every_hourly():
    """every(3600) should align to the top of each hour."""
    task = PeriodicTask.every(3600, _noop)
    half_past = datetime(2024, 1, 1, 12, 30, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = half_past
        # Next top-of-hour is 13:00:00 — 30 minutes away
        assert task._next_delay() == pytest.approx(1800.0)


def test_every_one_second_just_after_boundary():
    """At T+0.5 sec past a 1-second boundary, we wait 0.5 sec."""
    task = PeriodicTask.every(1, _noop)
    just_past = datetime(2024, 1, 1, 12, 0, 0, microsecond=500_000)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = just_past
        assert task._next_delay() == pytest.approx(0.5, abs=1e-3)


# --- minutely / hourly are thin shortcuts over every() ---


def test_minutely_matches_every_60():
    task = PeriodicTask.minutely(_noop)
    halfway = datetime(2024, 1, 1, 12, 0, 30)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = halfway
        assert task._next_delay() == pytest.approx(30.0)


def test_hourly_matches_every_3600():
    task = PeriodicTask.hourly(_noop)
    half_past = datetime(2024, 1, 1, 12, 30, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = half_past
        assert task._next_delay() == pytest.approx(1800.0)


# --- PeriodicTask.daily ---


def test_daily_later_today():
    """Target time is later today → fire today."""
    task = PeriodicTask.daily(18, 0, _noop)
    noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = noon
        assert task._next_delay() == pytest.approx(6 * 3600.0)


def test_daily_already_passed_today():
    """Target time already passed today → fire tomorrow."""
    task = PeriodicTask.daily(10, 0, _noop)
    noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = noon
        # 10:00 already passed → next is tomorrow 10:00 = 22 hours away
        assert task._next_delay() == pytest.approx(22 * 3600.0)


# --- PeriodicTask.weekly ---

# datetime(2024, 1, 1) is a Monday; (2024, 1, 3) is a Wednesday.


def test_weekly_same_day_future_time():
    """Target weekday is today, target time is later today → fire today."""
    task = PeriodicTask.weekly(0, 18, 0, _noop)
    monday_noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = monday_noon
        # 12:00 → 18:00 same day = 6 hours
        assert task._next_delay() == pytest.approx(6 * 3600.0)


def test_weekly_same_day_past_time_jumps_to_next_week():
    """Target weekday is today but target time has passed → fire next week."""
    task = PeriodicTask.weekly(0, 10, 0, _noop)
    monday_noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = monday_noon
        # 10:00 already passed → wait until next Monday 10:00 = 7d - 2h
        assert task._next_delay() == pytest.approx(7 * 86400 - 2 * 3600)


def test_weekly_later_in_week():
    """Target weekday is later this week → fire that day."""
    task = PeriodicTask.weekly(4, 18, 0, _noop)  # Friday 6 PM
    monday_noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = monday_noon
        # Mon noon → Fri 6 PM = 4 days + 6 hours
        assert task._next_delay() == pytest.approx(4 * 86400 + 6 * 3600)


def test_weekly_target_weekday_passed_this_week():
    """Target weekday was earlier this week → fire next week."""
    task = PeriodicTask.weekly(0, 10, 0, _noop)  # Monday 10 AM
    wednesday_noon = datetime(2024, 1, 3, 12, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = wednesday_noon
        # Wed noon → next Mon 10 AM = 5 days - 2 hours
        assert task._next_delay() == pytest.approx(5 * 86400 - 2 * 3600)


def test_weekly_same_target_today_already_fired():
    """Target weekday is today, target time was earlier today → fire next week
    at the same time (not 6 days + a bit)."""
    task = PeriodicTask.weekly(2, 6, 30, _noop)  # Wednesday 6:30 AM
    wednesday_10am = datetime(2024, 1, 3, 10, 0, 0)
    with patch("common.periodicTask.datetime") as dt:
        dt.now.return_value = wednesday_10am
        # 6:30 AM already passed today → next Wed at 6:30 AM = 7d - 3.5h
        expected = 7 * 86400 - (3 * 3600 + 30 * 60)
        assert task._next_delay() == pytest.approx(expected)


# --- helpers ---


async def _noop():
    pass
