# DEVELOPMENT.md

## Getting Started

See [Setup](../README.md#setup) for environment setup.

One-time setup for the pre-push hooks:

```bash
pip install pre-commit
pre-commit install --hook-type pre-push
```

This runs [Ruff](https://docs.astral.sh/ruff/) (lint + format) and the full test suite on every `git push`. A push is blocked if either fails.

## Adding Features

Typical workflow:

1. Create a component in `components/` with pure functions that return string or embed data.
2. Add slash commands under `commands/` that call the component. See [commands/README.md](../commands/README.md) for structure and reference files.
3. Write tests. See [Automated Testing](#automated-testing) below.
4. [Run the bot in Docker](../README.md#run-application-using-docker-recommended) and verify your changes behave as expected.
5. Push. The pre-push hook verifies lint and tests pass.

If you use Claude Code, the [`slash-command-tester`](../.claude/skills/slash-command-tester.md) skill automates step 3: it ensures that a test exists, walks you through writing one if not, and catches unintentional behavior changes.

## Coding Rules

### Async / non-blocking
The bot runs on a single asyncio event loop. Any blocking call inside `async def` freezes heartbeats, voice, and every other command.

Keep everything non-blocking:

- HTTP → `common.utils.async_get_request` / `async_post_request` (aiohttp)
- Google APIs → `aiogoogle`
- Unavoidable sync libraries (e.g. `yt-dlp`) → wrap with `asyncio.to_thread(fn, *args)`
- Recurring/scheduled work → `AsyncTask/PeriodicTask` (see `common/asyncTask.py`/`common/periodicTask.py`); never `while True: sleep(...)`.

### Error handling

Catch exceptions in event handlers and component functions. Return a context-specific error string (e.g. `f"Error fetching leaderboard: {e}"`) rather than letting exceptions propagate silently.

## Automated Testing

Automated tests run in Docker.

```bash
./run-tests.sh                                    # all tests
./run-tests.sh tests/immediate/test_meme.py -v     # single feature
```

### Testing philosophy

All tests inject at the dispatch boundary (the highest practical level). The WebSocket receive/parse path (discord.py internals) is not exercised. Testing it would require a mock Discord server that stays in sync with discord.py's expected gateway payloads across versions, a maintenance cost that outweighs the benefit for this project.

- Gateway events (messages, reactions, member joins): `dpytest.message(...)` or `client.dispatch(...)`
- Slash commands: `invoke_slash(...)`. dpytest doesn't support interactions, so we built this.
- Background tasks: `@pytest.mark.looptime`. Real tasks fire via fast-forwarded asyncio time. See `tests/background/` directory.
- Voice callbacks: Capture `after=` from `vc.play()`, invoke it to trigger `_schedule_next_song` → `play_song()`.

### Immediate vs background tests

**The decision rule:**

> If I deleted everything after `invoke_slash(...)` (or `client.dispatch(...)`) returns, can my assertions still run?
> - **Yes** → `tests/immediate/`
> - **No** → `tests/background/`

**Example.** `/music play` has tests in both folders:

- `test_music_play_no_results` asserts on the "couldn't find" reply — assertions run immediately. → `immediate/`
- `test_music_play_single_song_adds_to_queue` awaits `asyncio.gather(*musicPlayer._PENDING_TASKS)` and asserts on `vc.play` being called — assertions need the background task to finish. → `background/`

**What each folder is for:**

| Folder | Use for |
|---|---|
| `tests/immediate/` | Slash commands, modals, gateway-event handlers that complete synchronously. |
| `tests/background/` | Autostarted periodic tasks, **or** commands that return immediately but kick off async work whose effects the test asserts on. |

**Conftest autouse machinery (you don't need to think about it, but here's what's running):**

| Folder | Autouse | Purpose |
|---|---|---|
| `tests/immediate/conftest.py` | `tasks_noop` | Disables `PeriodicTask.start` / `AsyncTask.start`, so nothing leaks into the background during a sync test. |
| `tests/background/conftest.py` | `db_dir` (via `_ensure_db_dir`) | Every background test gets a fresh shelve dir (tasks write to disk). |
| `tests/background/conftest.py` | `_looptime_clock` | Patches `datetime.now()` inside `PeriodicTask` to track looptime's fake clock — without it, periodic tasks hang under `@pytest.mark.looptime`. |

Background tests must add `pytestmark = [pytest.mark.looptime]` at module level to enable the fake-clock fast-forward.

### Dispatch patterns

Assert on observable behavior (response substrings, DB state, captured messages).

A forgotten `register_subcommand` or missing test is caught by the [coverage guard](../tests/test_command_coverage.py).

| Entry point | Helper | Example |
|---|---|---|
| Slash command (`@group.command`) | `invoke_slash(tree, "dota list", user, guild)` | `tests/immediate/test_dota.py` |
| Gateway event (`@client.event`) | `dpytest.message(...)` or `client.dispatch(...)` | `tests/immediate/test_emote.py` (immediate) / `tests/background/test_movie.py` (kicks off background) |
| Periodic/Async task (`PeriodicTask` / `AsyncTask`) | `@pytest.mark.looptime` + trigger (`init()` or gateway event) | `tests/background/test_dota.py` / `tests/background/test_movie.py` |
| Modal (`discord.ui.Modal`) | Instantiate modal, call `on_submit(interaction)` directly | `tests/immediate/test_movie.py` |
| Voice callback (`vc.play`'s `after=`) | Capture `after=` from `vc.play()`, invoke it | `tests/background/test_music.py` |

### Adding a test

1. **Command or event?** → `tests/immediate/test_<feature>.py`. Use `invoke_slash(...)` for commands, `dpytest.message(...)`/`client.dispatch(...)` for events.
2. **Background task?** → `tests/background/test_<feature>.py`. Call `component.init()`, then `await asyncio.sleep(interval)` to trigger it.
3. **Need test data?** → Use `seeded_<feature>_db` fixture or build state inline.
4. **Need to stub an API?** → Use helpers from `tests/_stubs.py`.

#### Fixtures

Tests use the production `CommandTree` built by `commands.load_commands(tree)`. The session-scoped `tree` fixture in `tests/conftest.py` constructs it once per test session.

Other shared fixtures in `tests/conftest.py` include:

| Fixture | Purpose |
|---|---|
| `tree` | Production command tree |
| `guild` / `admin_member` / `regular_member` | Test guild with members |
| `db_dir` / `seeded_<feature>_db` | Temp database, optionally pre-seeded |
| `tasks_noop` | Disables all background task scheduling (autouse in `immediate/`) |
| `ut_client_ready` / `dpytest_client` | Event loop + dpytest wiring |

#### Stubs

External I/O is stubbed at the library boundary, not at the production helper that calls it. Centralized stubs live in `tests/_stubs.py`:

| Dependency | Stub | Patch target |
|---|---|---|
| HTTP (Dota) | `stub_dota_api(monkeypatch, ...)` | `ut.async_get_request` |
| HTTP (Twitch) | `stub_twitch_api(monkeypatch, ...)` | `ut.async_get_request` / `async_post_request` |
| YouTube + yt-dlp | `stub_youtube(monkeypatch, ...)` | `musicPlayer.Aiogoogle` / `musicPlayer.YoutubeDL` |
| Discord channels (capturing) | `patch_bot_channel` / `patch_main_channel` / `patch_channel(name)` | `ut.botChannel` / `ut.mainChannel` / `ut.guildObject.channels` |
| Discord scheduled events | `patch_movie_event_present` / `patch_movie_event_missing` | `ut.guildObject.scheduled_events` |
| Voice client | `fake_vc` fixture in `tests/conftest.py` | `musicPlayer.vc` |

**Library-boundary means "the line where our code calls into discord.py / aiohttp / yt-dlp."** Patching helpers in `common/utils.py` or `components/` is wrong — it bypasses the code under test, and a rename of the helper passes tests while breaking prod. Concrete: `monkeypatch.setattr(ut, "get_role", lambda _: my_role)` is the violation; the fix is to grab the bootstrapped role with the real `ut.get_role(ut.env["ADMIN_ROLE"])` and mutate the field you care about (e.g., `.members = []`).

#### Bootstrap defaults

`tests/_env_setup.py` ships the test guild with named channels (`MEME_CHANNEL`, `DOTA_CHANNEL`, `MOVIE_CHANNEL`) and roles (`ADMIN_ROLE`, `MOVIE_ROLE`, `WELCOME_ROLE`) already on `ut.guildObject`. Production code that calls `ut.get_channel(name)` / `ut.get_role(name)` resolves naturally without per-test patching.

The default channels are **fail-loud**: their `.send` raises

> `AssertionError: Test sent to channel 'X' without patching. Call patch_channel(monkeypatch, 'X').`

If you see that, your test exercised a send path on a channel that needs a capturing version. Call `patch_channel(monkeypatch, ut.env["X_CHANNEL"])` and assert on its `.messages`.

#### Common Patterns

Reference these tests for non-obvious cases:

| Pattern | Reference | Key Insight |
|---|---|---|
| `discord.Member` params | `tests/immediate/test_dota.py:test_dota_add_success` | Pass `make_member()` directly in options; `invoke_slash` handles resolved data |
| Module-level state reset | `tests/immediate/test_music.py:fresh_music_state` | `autouse=True` fixture to reset globals if needed |
| Modal submission | `tests/immediate/test_movie.py:test_movie_add_suggestion_modal_submit_adds_to_db` | Instantiate modal, set `TextInput._value`, call `on_submit` |

## Tooling

Run the linter manually:
```bash
pre-commit run --all-files
```
To bump Ruff to the latest version: `pre-commit autoupdate`.

## Update Dependencies

This project uses [pip-tools](https://pip-tools.readthedocs.io/) to manage dependencies. To update dependencies:

```bash
pip install pip-tools
pip-compile --upgrade requirements.in
```

## Built With

* [discord.py](https://discordpy.readthedocs.io/en/latest/) - Discord API wrapper
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube audio extraction for music player
* [aiogoogle](https://github.com/omarryhan/aiogoogle) - Async Google APIs for video metadata
* [ffmpeg](https://ffmpeg.org/) - Audio processing for voice channels
