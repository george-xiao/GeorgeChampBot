"""Template for adding a periodic task to a component module.

Periodic tasks fire a coroutine on a recurring schedule (e.g. every 15
minutes, or every Friday at noon). They replace polling patterns like
checking `datetime.now()` inside a tight loop.

The pattern uses `common.asyncTask.make_periodic_task` plus a scheduling
helper from the same module:
  - `aligned_interval(seconds)` — fires at clock boundaries aligned to N
    seconds. e.g. `aligned_interval(900)` fires at :00, :15, :30, :45.
  - `weekly_at(weekday, hour, minute)` — fires once a week at the given
    local time. weekday is 0=Monday ... 6=Sunday.

To add a new periodic task, copy this template into your component module
(`components/<feature>.py`) and replace the placeholders:
  <TASK_NAME>        — uppercase identifier (e.g. RECENT_MATCHES_TASK)
  <schedule>         — call to a scheduling helper, e.g.
                        aligned_interval(3600)
                        weekly_at(ut.env["ANNOUNCEMENT_DAY"], ut.env["ANNOUNCEMENT_HOUR"], ut.env["ANNOUNCEMENT_MIN"])
  <coroutine>        — existing async function to fire. If it takes args
                        that need late binding (e.g. a channel object),
                        wrap in a lambda:
                        `lambda: check_recent_matches(ut.get_channel(...))`

If your component has MULTIPLE periodic tasks, define one `_X_TASK` per
task and start them all from a single `init()` (see `components/memeReview.py`
or `components/musicPlayer.py`).

After defining the module, add `<your_module>.init()` to GeorgeChampBot.py's
on_ready handler, after slash command setup.
"""

import common.utils as ut
from common.asyncTask import make_periodic_task, aligned_interval, weekly_at


_<TASK_NAME> = None


def init():
    """Start the periodic <description> task."""
    global _<TASK_NAME>
    _<TASK_NAME> = make_periodic_task(<schedule>, <coroutine>)
    _<TASK_NAME>.start()


async def <coroutine>():
    """The actual work that runs on each tick."""
    ...
