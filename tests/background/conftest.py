import asyncio
from datetime import datetime

import pytest


@pytest.fixture(autouse=True)
def _ensure_db_dir(db_dir):
    """Force db_dir creation for every background test (tasks write to shelve DBs)."""


@pytest.fixture(autouse=True)
def _looptime_clock(monkeypatch):
    """Make PeriodicTask's wall clock advance with looptime's fake clock.

    PeriodicTask's `every`/`daily`/`weekly` compute their delay from
    `datetime.now()` so tasks fire aligned to real-clock boundaries. looptime
    fast-forwards the *event-loop* clock, not the wall clock, so a wall-clock
    delay never elapses under looptime and the task loop wedges.

    We leave the production schedule math untouched and only swap the clock it
    reads: `datetime.now()` now tracks `loop.time()` (the fake clock). The real
    boundary math then runs on fake time -- the first firing lands inside the
    first period (prod fires at the next boundary, < period away) and every
    firing after is a full period apart. So `await asyncio.sleep(<period>)`
    lands exactly one firing per period, matching how these tests are written.

    BASE is a fixed, arbitrary epoch that is not aligned to any period boundary,
    so the first delay is strictly inside the period (no boundary tie with the
    test's own sleep).
    """
    import common.periodicTask as periodic_task

    BASE = 1_700_000_000.0

    class _LoopClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(BASE + asyncio.get_running_loop().time())

    monkeypatch.setattr(periodic_task, "datetime", _LoopClock)
