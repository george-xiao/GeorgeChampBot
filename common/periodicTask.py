from datetime import datetime, timedelta
from typing import Callable, Coroutine
import asyncio

from common.asyncTask import AsyncTask


class PeriodicTask(AsyncTask):
    """
    A recurring background task. Construct via the classmethod factories
    (`every`, `minutely`, `hourly`, `daily`, `weekly`) rather than the bare
    constructor — each factory wires the schedule math for you.

    Example:
        PeriodicTask.every(900, check_streams).start()
        PeriodicTask.daily(hour=11, minute=0, coroutine_factory=morning_reminder).start()
        PeriodicTask.weekly(weekday=4, hour=18, minute=0, coroutine_factory=friday_announce).start()
    """

    def __init__(
        self,
        next_delay: Callable[[], float],
        coroutine_factory: Callable[[], Coroutine],
    ):
        self._next_delay = next_delay

        async def _loop():
            while True:
                delay = next_delay()
                if delay > 0:
                    await asyncio.sleep(delay)
                await coroutine_factory()

        super().__init__(lambda: _loop())

    @classmethod
    def every(cls, seconds: int, coroutine_factory: Callable[[], Coroutine]) -> "PeriodicTask":
        """Fire at clock boundaries aligned to `seconds`.

        Example: `every(900, ...)` fires at :00, :15, :30, :45 of each hour.
        Alignment is against UTC epoch seconds, so `every(86400, ...)` fires
        at UTC midnight (use `daily(0, 0, ...)` for local midnight).
        """
        def _compute() -> float:
            now = datetime.now().timestamp()
            next_boundary = (now // seconds + 1) * seconds
            return next_boundary - now
        return cls(_compute, coroutine_factory)

    @classmethod
    def minutely(cls, coroutine_factory: Callable[[], Coroutine]) -> "PeriodicTask":
        """Fire at the top of every minute."""
        return cls.every(60, coroutine_factory)

    @classmethod
    def hourly(cls, coroutine_factory: Callable[[], Coroutine]) -> "PeriodicTask":
        """Fire at the top of every hour."""
        return cls.every(3600, coroutine_factory)

    @classmethod
    def daily(cls, hour: int, minute: int, coroutine_factory: Callable[[], Coroutine]) -> "PeriodicTask":
        """Fire at the next occurrence of the given hour:minute (local time)."""
        def _compute() -> float:
            now = datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return (target - now).total_seconds()
        return cls(_compute, coroutine_factory)

    @classmethod
    def weekly(
        cls,
        weekday: int,
        hour: int,
        minute: int,
        coroutine_factory: Callable[[], Coroutine],
    ) -> "PeriodicTask":
        """Fire at the next occurrence of weekday@hour:minute (local time).

        `weekday`: 0 = Monday ... 6 = Sunday (matches `datetime.weekday()`).
        """
        def _compute() -> float:
            now = datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = (weekday - now.weekday()) % 7
            target += timedelta(days=days_ahead)
            if target <= now:
                target += timedelta(days=7)
            return (target - now).total_seconds()
        return cls(_compute, coroutine_factory)
