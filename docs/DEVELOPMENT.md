# DEVELOPMENT.md

## Standard Development Process

See [Setup](../README.md#setup) and [Run Application Using Docker](../README.md#run-application-using-docker-recommended) for environment setup. Develop in Docker; production is Linux, so verify any shell-script changes work there too (GitBash works for Windows users).

### Adding new features
See the [discord.py app-commands docs](https://discordpy.readthedocs.io/en/stable/interactions/api.html#application-commands) and [commands README](../commands/README.md) for the slash-command authoring workflow.

### Async / non-blocking
The bot runs on a single asyncio event loop (discord.py). Any synchronous blocking call inside an `async def` — `requests`, `time.sleep`, sync database drivers, sync HTTP/library APIs — freezes every gateway heartbeat, voice tick, and concurrent slash command until it returns. New code must stay non-blocking:

- HTTP → `common.utils.async_get_request` / `async_post_request` (aiohttp).
- Google APIs → `aiogoogle` (already a dependency).
- Unavoidable sync libraries (e.g. `yt-dlp`'s `extract_info`) → wrap with `asyncio.to_thread(fn, *args)`.
- Recurring/scheduled work → `PeriodicTask` (see `common/periodicTask.py`); never `while True: time.sleep(...)`.

## Testing

Tests run in Docker via the `test` stage of the `Dockerfile`, which extends the `base` layer with `requirements-test.txt`.

```bash
./run-tests.sh                          # all tests
./run-tests.sh tests/test_meme.py -v    # single feature
SNAPSHOT_UPDATE=1 ./run-tests.sh        # (re)write snapshots
```

Snapshot tests live in `tests/test_<feature>.py` and lock each slash command's output into `tests/snapshots/<feature>/<command>.json`. The `.claude/skills/slash-command-tester.md` skill automates the write/diff workflow for Claude Code users.

## Update Dependencies

This project uses [pip-tools](https://pip-tools.readthedocs.io/) to manage dependencies. To update dependencies:

```
pip install pip-tools
pip-compile --upgrade requirements.in
```

## Built With

* [discord.py](https://discordpy.readthedocs.io/en/latest/) - Discord API wrapper
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube audio extraction for music player
* [google-api-python-client](https://github.com/googleapis/google-api-python-client) - YouTube API for video metadata
* [ffmpeg](https://ffmpeg.org/) - Audio processing for voice channels