# GeorgeChampBot:

**New Features:**
- [ ] Standardize messages. Colors, images, etc. Use embedded messages. At the minimum, Message sending class should have a template for errors.
- [ ] Add a pre-commit hook for linters/formatters. This will force devs to maintain code quality before merging code. .vscode/settings.json references some linters we can use
- [ ] Create class for logging. Georgechamp bot should write application logs for debugging in a local file. Stretch goal is to print in a #log channel. Log should have timestamp, filename, line number, component name, and log message.Logging debug information.
- [ ] Shell script for dependency installs.
- [ ] Role assigning feature
- [ ] Movie vote workflow

**Bugs:**
- [ ] Refactor existing commands to use slash commands instead

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

**Bugs:**
- [ ] Multiple page in leaderboard doesn't work

## Music Bot:

**Bugs:**
- [ ] Performance issues when queueing multiple songs

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
- [ ] Make upcomingMovie.py more generic (Do X every Y minutes)
- [ ] Make eventReminder.py more generic (Do X in Y minutes)

**Bugs:**
- [ ] Picking host when event does not exist does not save the host

**Nits:**
- [ ] Handle event creation. if an event doesn't exist, create one. If multiple Movie Night event exists, keep the newest one. (Impossible to do right now due to Discord API bug where editing an event will sometimes cause the event ID to change as well; will have to wait for Discord API to make behavior more consistent).
- [ ] Send a second movie night alert closer to start time
- [ ] Remove remove-host command if it is not being used for a sufficient amount of time (Currently, the command is commented out).
- [ ] Have a consistent spelling of movie-night (vs movie night?)
 
