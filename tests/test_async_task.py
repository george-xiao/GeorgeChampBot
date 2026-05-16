"""Unit tests for the scheduling helpers in common/asyncTask.py.

These are pure functions of the current clock — easy to test by freezing
datetime.now(). No event loop needed; the schedulers themselves are sync.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from common.asyncTask import aligned_interval, weekly_at


# --- aligned_interval ---

def test_aligned_interval_on_boundary_returns_full_interval():
    """When the current time is exactly on a boundary, the next boundary is
    one full interval away — we don't fire on the current moment."""
    fn = aligned_interval(60)
    on_boundary = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = on_boundary
        assert fn() == pytest.approx(60.0)


def test_aligned_interval_partway_through():
    fn = aligned_interval(60)
    halfway = datetime(2024, 1, 1, 12, 0, 30)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = halfway
        assert fn() == pytest.approx(30.0)


def test_aligned_interval_quarter_hour():
    """aligned_interval(900) should align to :00, :15, :30, :45."""
    fn = aligned_interval(900)
    seven_minutes_thirty_seconds_in = datetime(2024, 1, 1, 12, 7, 30)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = seven_minutes_thirty_seconds_in
        # Next boundary is 12:15:00 — 7m30s away
        assert fn() == pytest.approx(450.0)


def test_aligned_interval_hourly():
    """aligned_interval(3600) should align to the top of each hour."""
    fn = aligned_interval(3600)
    half_past = datetime(2024, 1, 1, 12, 30, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = half_past
        # Next top-of-hour is 13:00:00 — 30 minutes away
        assert fn() == pytest.approx(1800.0)


def test_aligned_interval_one_second_just_after_boundary():
    """At T+0.5 sec past a 1-second boundary, we wait 0.5 sec."""
    fn = aligned_interval(1)
    just_past = datetime(2024, 1, 1, 12, 0, 0, microsecond=500_000)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = just_past
        assert fn() == pytest.approx(0.5, abs=1e-3)


# --- weekly_at ---

# datetime(2024, 1, 1) is a Monday; (2024, 1, 3) is a Wednesday.

def test_weekly_at_same_day_future_time():
    """Target weekday is today, target time is later today → fire today."""
    fn = weekly_at(weekday=0, hour=18, minute=0)
    monday_noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = monday_noon
        # 12:00 → 18:00 same day = 6 hours
        assert fn() == pytest.approx(6 * 3600.0)


def test_weekly_at_same_day_past_time_jumps_to_next_week():
    """Target weekday is today but target time has passed → fire next week."""
    fn = weekly_at(weekday=0, hour=10, minute=0)
    monday_noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = monday_noon
        # 10:00 already passed → wait until next Monday 10:00 = 7d - 2h
        assert fn() == pytest.approx(7 * 86400 - 2 * 3600)


def test_weekly_at_later_in_week():
    """Target weekday is later this week → fire that day."""
    fn = weekly_at(weekday=4, hour=18, minute=0)  # Friday 6 PM
    monday_noon = datetime(2024, 1, 1, 12, 0, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = monday_noon
        # Mon noon → Fri 6 PM = 4 days + 6 hours
        assert fn() == pytest.approx(4 * 86400 + 6 * 3600)


def test_weekly_at_target_weekday_passed_this_week():
    """Target weekday was earlier this week → fire next week."""
    fn = weekly_at(weekday=0, hour=10, minute=0)  # Monday 10 AM
    wednesday_noon = datetime(2024, 1, 3, 12, 0, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = wednesday_noon
        # Wed noon → next Mon 10 AM = 5 days - 2 hours
        assert fn() == pytest.approx(5 * 86400 - 2 * 3600)


def test_weekly_at_same_target_today_already_fired():
    """Target weekday is today, target time was earlier today → fire next week
    at the same time (not 6 days + a bit)."""
    fn = weekly_at(weekday=2, hour=6, minute=30)  # Wednesday 6:30 AM
    wednesday_10am = datetime(2024, 1, 3, 10, 0, 0)
    with patch("common.asyncTask.datetime") as dt:
        dt.now.return_value = wednesday_10am
        # 6:30 AM already passed today → next Wed at 6:30 AM = 7d - 3.5h
        expected = 7 * 86400 - (3 * 3600 + 30 * 60)
        assert fn() == pytest.approx(expected)
