from datetime import datetime, timedelta
from typing import Callable, Coroutine, Tuple
import asyncio


class AsyncTask:
    """
    AsyncTasks are objects designed to encapsulate background tasks which run asynchronously.
    This is very useful for performing asynchronous operations without creating race conditions and timing issues.
    Note that at most only one instance of the background task will be active at any given time.
    The background task must be provided to the initializer as a function that returns a coroutine function.

    Example usage:
        1) Send a reminder to the host every morning at 11 am to pick a movie.
        2) Notify all participants that movie night starts within an hour.

    Documentation: https://docs.python.org/3/library/asyncio-task.html
    """

    def __init__(self, coroutine_factory: Callable[[], Coroutine]):
        """
        coroutine_factory: A function that returns coroutine function. Can be passed as:
            1) A coroutine_factory:
                def coroutine_factory():
                    sample_coroutine()
                AsyncTask(coroutine_factory)
            2) A lambda function:
                AsyncTask(lambda: sample_coroutine())

            Signature for sample_coroutine():
                - async def sample_coroutine() -> None
        """
        self.async_task: asyncio.Task | None = None
        self.coroutine_factory = coroutine_factory

    def start(self, *args: Tuple):
        """
        Starts the asynchronous task.
        Any existing task under this object will be stopped.
        """
        self.stop()

        if args:
            self.async_task = asyncio.create_task(self.coroutine_factory(args))
        else:
            self.async_task = asyncio.create_task(self.coroutine_factory())

    def stop(self):
        """
        Stops the asynchronous task, if it exists.
        """
        if self.async_task:
            self.async_task.cancel()
            self.async_task = None


def make_periodic_task(
    seconds_until_next: Callable[[], float],
    coroutine_factory: Callable[[], Coroutine],
) -> AsyncTask:
    """Build an AsyncTask that fires `coroutine_factory()` repeatedly on a schedule.

    `seconds_until_next` is called before each iteration and returns the delay
    until the next desired fire time. This lets callers express both clock-aligned
    intervals (use `aligned_interval`) and time-of-week schedules (use `weekly_at`).
    """
    async def _loop():
        while True:
            delay = seconds_until_next()
            if delay > 0:
                await asyncio.sleep(delay)
            await coroutine_factory()
    return AsyncTask(lambda: _loop())


def aligned_interval(seconds: int) -> Callable[[], float]:
    """Build a `seconds_until_next` callable that fires at clock boundaries
    aligned to `seconds`.

    Example: `aligned_interval(900)` fires at :00, :15, :30, :45 of each hour.
    Matches the old while-loop behavior of `if minute % 15 == 0 and second == 0`.
    """
    def _compute() -> float:
        now = datetime.now().timestamp()
        next_boundary = (now // seconds + 1) * seconds
        return next_boundary - now
    return _compute


def weekly_at(weekday: int, hour: int, minute: int) -> Callable[[], float]:
    """Build a `seconds_until_next` callable that fires at the next occurrence
    of the given weekday@hour:minute (local time).

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
    return _compute
