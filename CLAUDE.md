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
  asyncTask.py         # AsyncTask class for background operations
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
1. **AsyncTask** instead of the global while loop in `on_ready()` (the global loop is deprecated and causes race conditions)
2. **Slash commands** for all user-facing commands. Any code change that could affect slash command output triggers `.claude/skills/slash-command-tester.md` — it runs the snapshot tests and prompts on drift (update snapshot or fix code).
3. **Components directory** for new feature modules
4. **utils.py** for Discord objects - never create duplicate client instances

**AsyncTask usage:**
```python
from common.asyncTask import AsyncTask

task = AsyncTask(my_coroutine_factory)
task.start()  # Cancels previous run and starts new
task.stop()   # Cancels running task
```

**Database:** Uses Python's shelve for persistence. Always properly open/close shelve files.

**Error handling:** Catch exceptions in event handlers - errors are logged to mainChannel.

## Testing

Tests run inside Docker (no local Python pollution). The `test` stage of the multi-stage `Dockerfile` shares the `base` layer with the bot, then adds `requirements-test.txt` (pinned via `pip-compile --constraint=requirements.txt`).

`run-tests.sh` is primarily invoked by the `slash-command-tester` skill, but is also safe to run manually:

```bash
./run-tests.sh                          # all tests
./run-tests.sh tests/test_meme.py -v    # single feature
SNAPSHOT_UPDATE=1 ./run-tests.sh        # (re)write snapshots
```

Snapshot tests live in `tests/test_<feature>.py` and lock the output of each slash command into `tests/snapshots/<feature>/<command>.json`. See `.claude/skills/slash-command-tester.md` for the full workflow (when to fire, how to handle drift, how to write a test from scratch).

## Configuration

Copy `.env.template` to `.env`. Key variables:
- `DISCORD_TOKEN`, `DISCORD_GUILD`, `BOT_ID` - Core Discord config
- Channel names without `#`, roles without `@`
- `ANNOUNCEMENT_DAY` = 0-6 (Mon-Sun), `ANNOUNCEMENT_HOUR` = 0-23

## Known Technical Debt

- Global while loop in `on_ready()` should use AsyncTask pattern
- Standard emojis not working (noted TODO in code)
- OrderedShelve is a workaround for insertion-order shelve
