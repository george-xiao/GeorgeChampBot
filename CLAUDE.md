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
GeorgeChampBot.py      # Entry point, @ut.client.event handlers, main()
common/
  utils.py             # Shared Discord client, guild, channels, config
  asyncTask.py         # AsyncTask base class (one-shot async work)
  periodicTask.py      # PeriodicTask: AsyncTask + cron-style schedule factories
  orderedShelve.py     # Ordered shelve wrapper
  dota/                # Dota constants (game modes, heroes)
commands/              # Slash command tree (see commands/README.md)
components/            # Feature modules
  emoteLeaderboard.py  # Emoji reaction tracking
  musicPlayer.py       # Music queue/playback with yt-dlp
  memeReview.py        # Meme submission and voting
  movieNight.py        # Movie night scheduled-event handlers + SUGGESTION_DATABASE
  dotaReplay.py        # Dota 2 match tracking (OpenDota API)
  twitchAnnouncement.py # Twitch live notifications
  subcomponents/movieNight/  # upcomingMovie, eventReminder, suggestionDatabase, Movie
tests/                 # Integration tests; see docs/DEVELOPMENT.md#testing
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
1. **Event-driven async, never block the loop.** The bot runs a single asyncio event loop — any blocking call inside `async def` (e.g. `requests`, `time.sleep`, sync HTTP, sync library APIs) freezes Discord heartbeats and every other slash command until it returns. For HTTP, use `ut.async_get_request` / `ut.async_post_request` (aiohttp-backed, in `common/utils.py`). For unavoidable sync libraries (yt-dlp, etc.) wrap with `asyncio.to_thread(...)`. See `docs/DEVELOPMENT.md#async--non-blocking` for the rationale.
2. **AsyncTask** for one-shot background work; **PeriodicTask** for recurring schedules (see usage block below). Components own their task(s) and expose an `init()` that `on_ready` calls. Reference: `components/dotaReplay.py:init`.
3. **Slash commands** for all user-facing commands. Any code change that could affect slash command output triggers `.claude/skills/slash-command-tester.md` — it runs the relevant integration test (or walks through writing one) and prompts on drift (update behavior assertions or fix code). Integration tests dispatch through `tree._call` via `invoke_slash`; see `docs/DEVELOPMENT.md#testing`.
4. **Components directory** for new feature modules
5. **utils.py** for Discord objects - never create duplicate client instances

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

Every test drives production code through a real dispatch entry point (`tree._call` for slash, `client.dispatch` or dpytest for gateway events, `run_periodic_once` for periodic tasks). Assertions are on observable behavior — substrings in responses, post-condition DB state, captured channel messages — not output snapshots. See [Testing in DEVELOPMENT.md](docs/DEVELOPMENT.md#testing) for the three dispatch patterns and how to add a new test.

## Configuration

Copy `.env.template` to `.env`. Key variables:
- `DISCORD_TOKEN`, `DISCORD_GUILD`, `BOT_ID` - Core Discord config
- Channel names without `#`, roles without `@`
- `ANNOUNCEMENT_DAY` = 0-6 (Mon-Sun), `ANNOUNCEMENT_HOUR` = 0-23

## Known Technical Debt

- Standard emojis not working (noted TODO in code)
- OrderedShelve is a workaround for insertion-order shelve
