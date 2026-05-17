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
```

### Integration-only by design

Every test drives production code through one of its real dispatch entry points. Assertions are on observable behavior (response substrings, post-condition DB state, captured channel messages) — there are no output snapshots. A renamed component function or a forgotten `register_subcommand` will fail an integration test before any other check catches it.

There are three dispatch patterns, one per entry-point type:

| Entry point | Helper | Example |
|---|---|---|
| Slash command (`@group.command`) | `tests/_dispatch.py:invoke_slash(tree, "dota list", user, guild)` | `test_dota.py` |
| Gateway event (`@client.event`) | `dpytest.message(...)` / `dpytest.add_reaction(...)` for the cases dpytest covers, otherwise `client.dispatch("event_name", *args)` with a mocked payload | `test_emote.py` (dpytest) / `test_movie.py` (bare dispatch) |
| Periodic task (`PeriodicTask.*`) | `tests/_dispatch.py:run_periodic_once(task)` after the component's `init()` wires it up | `test_dota.py`, `test_twitch.py` |

A modal-only path (`/movie add-suggestion`) goes through `Modal.on_submit(interaction)` since Discord modals don't traverse the command tree. The `play_song` lifecycle tests in `test_music.py` invoke `play_song()` directly — that's the dispatch boundary for `vc.play`'s `after=` callback when a track ends.

### Permitted non-integration tests

One file doesn't use dispatch, by design:

- `tests/test_periodic_task.py` — pure scheduling math (`_next_delay()`). No entry point exists to dispatch through.

Every other slash command, event handler, and periodic task must be exercised through its real dispatch boundary. If you add a new slash command file under `commands/`, you must add an integration test that calls it via `invoke_slash`; there is no smoke fallback that confirms the file at least imports.

### Adding tests

Tests dispatch through the same `app_commands.CommandTree` that production builds — one tree, all commands attached via `commands/__init__.py:load_commands(tree)`. The shared session-scoped `tree` fixture (in `tests/conftest.py`) constructs it once per test session and every test depends on it. Cross-feature wiring is exercised for free.

Other shared fixtures in `tests/conftest.py`:
- `guild` / `members` / `admin_member` / `regular_member` — test guild plus `DEFAULT_MEMBERS` from `tests/_factories.py`. The `guild` fixture also `monkeypatch`-installs itself onto `ut.guildObject` so component code that reads the singleton sees test data.
- `db_dir` / `seeded_<feature>_db` — chdir to a tmp path and (optionally) seed the feature's shelve DB.
- `patched_periodic_start` — disables `PeriodicTask.start` so a component's `init()` wires its task without launching the background scheduler.
- `ut_client_ready` / `dpytest_client` — bind `ut.client` to the test's event loop; the latter also wires it into dpytest's runner.

Per-feature state resets that don't generalize stay in the feature's test file as autouse fixtures (e.g., `tests/test_music.py:fresh_music_state`, `tests/test_twitch.py:reset_twitch_module_state`).

External I/O is stubbed at the library boundary, not at the production helper that calls it:

- HTTP → patch `common.utils.async_get_request` / `async_post_request`
- YouTube API → patch `musicPlayer.Aiogoogle` and `musicPlayer.YoutubeDL`
- Voice → `MagicMock(spec=discord.VoiceClient)` with tracked play/pause/disconnect

Patching at the helper level (e.g., `memeReview.check_meme`, `twitchAnnouncement._validate_twitch_username`) is what the old unit-test pattern did — it lets renames and refactors slip through. Stick to library-boundary stubs.

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