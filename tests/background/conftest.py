"""Autouse fixtures for background task tests.

Ensures every test gets a temp DB directory.
Wires PeriodicTask's wall clock to looptime's fake event-loop clock so `await asyncio.sleep(period)` triggers tasks.
"""

import asyncio
from datetime import datetime

import pytest


@pytest.fixture(autouse=True)
def _ensure_db_dir(db_dir):
    """Force db_dir creation for every background test (tasks write to shelve DBs)."""


@pytest.fixture(autouse=True)
def _looptime_clock(monkeypatch):
    """Make PeriodicTask's wall clock advance with looptime's fake clock.

    Problem: PeriodicTask computes delays from `datetime.now()`, but looptime
    only fast-forwards the `event-loop` clock.

    Fix: Monkeypatch `datetime.now()` in periodicTask to return a timestamp
    derived from `loop.time()`, so the production schedule math runs against
    the fake clock.

    Note: BASE is an arbitrary epoch not aligned to any period boundary,
    ensuring first delay < one full period.
    """
    import common.periodicTask as periodic_task

    BASE = 1_700_000_000.0

    class _LoopClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(BASE + asyncio.get_running_loop().time())

    monkeypatch.setattr(periodic_task, "datetime", _LoopClock)
