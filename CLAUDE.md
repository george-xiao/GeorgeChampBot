# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeorgeChampBot is a Python Discord bot built with discord.py. Features include music player, emoji usage tracking, meme review, movie night scheduling, Dota 2 match tracking, and Twitch streamer tracking.

## Commands

**Docker (recommended):**
```bash
./run.sh                                # run bot (Docker)
./run-tests.sh                          # all tests
./run-tests.sh tests/immediate/test_meme.py -v    # single feature
```

## Architecture

```
GeorgeChampBot.py      # Entry point, @ut.client.event handlers, main()
common/
  utils.py             # Shared Discord client, guild, channels, config (ut.*)
  asyncTask.py         # AsyncTask base class (one-shot async work)
  periodicTask.py      # PeriodicTask: AsyncTask + cron-style schedule factories
  orderedShelve.py     # Ordered shelve wrapper
  dota/                # Dota constants (game modes, heroes)
commands/              # Slash command tree (see commands/README.md)
components/            # Feature modules (pure functions + init() for periodic tasks)
  emoteLeaderboard.py  # Emoji usage tracking (chat + reactions)
  musicPlayer.py       # Music queue/playback with yt-dlp
  memeReview.py        # Meme submission and voting
  movieNight.py        # Movie night scheduling + suggestions
  dotaReplay.py        # Dota 2 match tracking (OpenDota API)
  twitchAnnouncement.py # Twitch streamer tracking
  subcomponents/movieNight/  # upcomingMovie, eventReminder, suggestionDatabase, Movie
tests/                 # Tests (see docs/DEVELOPMENT.md#automated-testing)
database/              # Shelve-based persistent storage (runtime created)
```

**Key shared objects from `common.utils`:**
- `client` - Discord client instance
- `commandTree` - Application command tree (slash commands)
- `guildObject` - Target Discord server
- `mainChannel`, `botChannel` - Channel references
- `env` - Configuration dict from .env

## Important Patterns

1. **Single client instance**: Use `ut.client` everywhere. Never create a second `discord.Client`.
2. **Never block the event loop**: See `docs/DEVELOPMENT.md#async--non-blocking`.
3. **AsyncTask/PeriodicTask**: AsyncTask for one-shot background work; PeriodicTask for recurring work. Components own their tasks and expose `init()` that `on_ready` calls. Reference: `common/asyncTask.py`, `common/periodicTask.py` and `components/dotaReplay.py:init`.
4. **Slash commands**: See `commands/README.md` for structure. Any change that could affect slash command output triggers `.claude/skills/slash-command-tester.md`.
5. **Error handling**: Catch exceptions everywhere. Event handlers log to `mainChannel`; slash command pure functions return an error string; periodic tasks send to their channel.
6. **Shelve access**: Use a context manager (`with shelve.open(...) as db:`). If not possible, suppress `SIM115`.
7. **Testing**: See `docs/DEVELOPMENT.md#automated-testing`. Stub at the library boundary, not production helpers.

## Configuration

Copy `.env.template` to `.env`. Key variables:
- `DISCORD_TOKEN`, `DISCORD_GUILD`, `BOT_ID` - Core Discord config
- Channel names without `#`, roles without `@`
- `ANNOUNCEMENT_DAY` = 0-6 (Mon-Sun), `ANNOUNCEMENT_HOUR` = 0-23

## Known Technical Debt

- Standard emojis not working (noted TODO in code)
- OrderedShelve is a workaround for insertion-order shelve
