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
