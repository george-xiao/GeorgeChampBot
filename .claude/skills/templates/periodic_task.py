"""Template for adding a periodic task to a component module.

Periodic tasks fire a coroutine on a recurring schedule (e.g. every 15
minutes, or every Friday at noon) via `common.periodicTask.PeriodicTask`
and one of its classmethod factories:
  - `PeriodicTask.every(seconds, fn)` — fires at clock boundaries aligned to N
    seconds. e.g. `every(900, ...)` fires at :00, :15, :30, :45.
  - `PeriodicTask.minutely(fn)` — fires at the top of every minute.
  - `PeriodicTask.hourly(fn)` — fires at the top of every hour.
  - `PeriodicTask.daily(hour, minute, fn)` — fires once a day at the given
    local time.
  - `PeriodicTask.weekly(weekday, hour, minute, fn)` — fires once a week at
    the given local time. weekday is 0=Monday ... 6=Sunday.

To add a new periodic task, copy this template into your component module
(`components/<feature>.py`) and replace the placeholders:
  <TASK_NAME>   — uppercase identifier (e.g. RECENT_MATCHES_TASK)
  <factory>     — call to a PeriodicTask factory, e.g.
                    PeriodicTask.every(3600, check_recent_matches)
                    PeriodicTask.weekly(ut.env["ANNOUNCEMENT_DAY"], ut.env["ANNOUNCEMENT_HOUR"], ut.env["ANNOUNCEMENT_MIN"], announcement_task)
  If your coroutine needs args that need late binding (e.g. a channel
  object), wrap in a lambda:
                    PeriodicTask.every(900, lambda: check_twitch_live(ut.mainChannel))

If your component has MULTIPLE periodic tasks, define one `_X_TASK` per
task and start them all from a single `init()` (see `components/memeReview.py`
or `components/musicPlayer.py`).

After defining the module, add `<your_module>.init()` to GeorgeChampBot.py's
on_ready handler, after slash command setup.
"""

import common.utils as ut
from common.periodicTask import PeriodicTask


_<TASK_NAME> = None


def init():
    """Start the periodic <description> task."""
    global _<TASK_NAME>
    _<TASK_NAME> = <factory>
    _<TASK_NAME>.start()


async def <coroutine>():
    """The actual work that runs on each tick."""
    ...
