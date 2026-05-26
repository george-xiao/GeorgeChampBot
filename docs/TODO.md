# GeorgeChampBot:

**New Features:**
- [ ] Standardize messages. Colors, images, etc. Use embedded messages. At the minimum, Message sending class should have a template for errors.
- [ ] Expand Ruff rule selection (see `pyproject.toml` for current selection). Deliberately left out for now:
    - [ ] `I` (isort) — import sorting. Autofixable, but reorders nearly every file on first run; land separately to keep the diff reviewable.
    - [ ] `PL` (pylint) — broad/opinionated. Consider enabling specific subrules (e.g. `PLR1733` for `.items()` lookups) rather than the whole group.
    - [ ] `E501` (line-too-long) — currently off because some lines exceed 300 chars. Re-enable after wrapping the long lines in `GeorgeChampBot.py` and tightening `line-length` in `pyproject.toml`.
- [ ] Create class for logging. Georgechamp bot should write application logs for debugging in a local file. Stretch goal is to print in a #log channel. Log should have timestamp, filename, line number, component name, and log message.Logging debug information.
- [ ] Shell script for dependency installs.
- [ ] Role assigning feature
- [ ] Movie vote workflow

**Nits:**
- [ ] Announcement lines can be modularized
- [ ] Make OrderedShelves use pickle module instead of shelves module
- [ ] Divide up utils into smaller files
- [ ] Validate .env file before starting up the bot (This will enable us to catch issues during startup and not runtime this way)
- [ ] Add small comments above all functions and methods
- [ ] Add type hints for all functions and methods

## Meme Review:

**Features:**
- [ ] Mechanism for hiding who sent meme
- [ ] Deprecate meme-review channel

**Bugs:**
- [ ] If same vote, person who sent first wins
- [ ] Changing votes on old memes causes them to be considered in 'Meme of the Week' (even if the old meme was not posted this week).

**Nits:**
- [ ] Move meme_emojis to .env
- [ ] Support for standard emojis
- [ ] Refactor to use classes

## Emote Leaderboard:

**Features:**
- [ ] Enable emote count for standard emotes

## Music Bot:

**Features:**
- [ ] Add cron job to run.sh to update ytdl dependency daily during off-times

**Bugs:**
- [x] Performance issues when queueing multiple songs (maybe addressed [remove if no issues surface when using]: process_input migrated to aiogoogle, extract_info wrapped in asyncio.to_thread — event loop no longer blocks during queueing)

**Nits:**
- [ ] Make queueing songs no longer O(n)

## Dota Replay:

**Features:**
- [ ] Notification should tell us if player won

**Bugs:**
- [ ] Hero Id is not sequential which is causing logic issues
- [ ] Bot misses games

## Movie Night:

**Features:**
- [ ] Notify channel if movie night date is updated
- [ ] Send a daily reminder to DatabaseOwner until he acknowledges updating Google Sheets
- [ ] Migrate upcomingMovie.py's reminder loop to `PeriodicTask.daily(12, 0, ...)` (`common/periodicTask.py` now provides the abstraction)
- [ ] Replace eventReminder.py's bare `AsyncTask` + `asyncio.sleep` pattern with a one-shot scheduling helper (counterpart to `PeriodicTask` for "do X in Y minutes")

**Bugs:**
- [ ] Picking host when event does not exist does not save the host

**Nits:**
- [ ] Handle event creation. if an event doesn't exist, create one. If multiple Movie Night event exists, keep the newest one. (Impossible to do right now due to Discord API bug where editing an event will sometimes cause the event ID to change as well; will have to wait for Discord API to make behavior more consistent).
- [ ] Send a second movie night alert closer to start time
- [ ] Remove remove-host command if it is not being used for a sufficient amount of time (Currently, the command is commented out).
- [ ] Have a consistent spelling of movie-night (vs movie night?)
 
## Development:

**Testing:**
- [ ] Add linting + testing when PR gets created (GitHub Actions)
