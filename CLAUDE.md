# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeorgeChampBot is a Python Discord bot built with discord.py 2.2.2. Features include music player, emoji tracking, meme review, movie nights, Dota 2 match tracking, and Twitch streamer announcements.

## Build & Run Commands

**Docker (recommended):**
```bash
./run.sh
```

**Local development:**
```bash
pip3 install -r requirements.txt
python3 GeorgeChampBot.py
```

**System dependencies (for local):** ffmpeg, python3-gdbm

## Architecture

```
GeorgeChampBot.py      # Entry point, event handlers, scheduled tasks
common/
  utils.py             # Shared Discord client, guild, channels, config
  asyncTask.py         # AsyncTask base class (one-shot async work)
  periodicTask.py      # PeriodicTask: AsyncTask + cron-style schedule factories
  memberDatabase.py    # Base class for persistent member tracking
  orderedShelve.py     # Ordered shelve wrapper
components/            # Feature modules
  emoteLeaderboard.py  # Emoji reaction tracking
  musicPlayer.py       # Music queue/playback with yt-dlp
  memeReview.py        # Meme submission and voting
  movieNight.py        # Movie night slash commands
  dotaReplay.py        # Dota 2 match tracking (OpenDota API)
  twitchAnnouncement.py # Twitch live notifications
database/              # Shelve-based persistent storage (runtime created)
```

**Key shared objects from `common.utils`:**
- `client` - Discord client instance
- `commandTree` - Application command tree (slash commands)
- `guildObject` - Target Discord server
- `mainChannel`, `botChannel` - Channel references
- `env` - Configuration dict from .env

## Important Patterns

**New features should use:**
1. **AsyncTask** for one-shot background work; **PeriodicTask** for recurring schedules (see usage block below). Components own their task(s) and expose an `init()` that `on_ready` calls. Template: `.claude/skills/templates/periodic_task.py`.
2. **Slash commands** for all user-facing commands. Any code change that could affect slash command output triggers `.claude/skills/slash-command-tester.md` — it runs the snapshot tests and prompts on drift (update snapshot or fix code).
3. **Components directory** for new feature modules
4. **utils.py** for Discord objects - never create duplicate client instances

**AsyncTask / PeriodicTask usage:**
```python
from common.asyncTask import AsyncTask
from common.periodicTask import PeriodicTask

# One-shot background coroutine
task = AsyncTask(my_coroutine_factory)
task.start()  # Cancels previous run and starts new
task.stop()   # Cancels running task

# Recurring (every 15 min, aligned to clock boundaries: :00, :15, :30, :45)
PeriodicTask.every(900, my_async_fn).start()

# Convenience shortcuts
PeriodicTask.minutely(my_async_fn).start()
PeriodicTask.hourly(my_async_fn).start()

# Recurring (daily at a specific local time)
PeriodicTask.daily(hour=11, minute=0, coroutine_factory=my_async_fn).start()

# Recurring (weekly at a specific local time; weekday 0=Mon ... 6=Sun)
PeriodicTask.weekly(weekday=4, hour=18, minute=0, coroutine_factory=my_async_fn).start()
```

**Database:** Uses Python's shelve for persistence. Always properly open/close shelve files.

**Error handling:** Catch exceptions in event handlers - errors are logged to mainChannel.

## Testing

See [Testing in DEVELOPMENT.md](docs/DEVELOPMENT.md#testing) for how to run the suite, the Docker `test` stage, and the snapshot-test workflow.

## Configuration

Copy `.env.template` to `.env`. Key variables:
- `DISCORD_TOKEN`, `DISCORD_GUILD`, `BOT_ID` - Core Discord config
- Channel names without `#`, roles without `@`
- `ANNOUNCEMENT_DAY` = 0-6 (Mon-Sun), `ANNOUNCEMENT_HOUR` = 0-23

## Known Technical Debt

- Standard emojis not working (noted TODO in code)
- OrderedShelve is a workaround for insertion-order shelve
