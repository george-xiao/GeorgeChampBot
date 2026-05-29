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

## Automated Integration Testing

Automated tests run in Docker.

```bash
./run-tests.sh                                     # all tests
./run-tests.sh tests/immediate/test_meme.py -v     # single feature
```

### Testing philosophy

All tests inject at the dispatch boundary (the highest practical level). The WebSocket receive/parse path (discord.py internals) is not exercised. Testing it would require a mock Discord server that stays in sync with discord.py's expected gateway payloads across versions, a maintenance cost that outweighs the benefit for this project.

Because each test runs the real code path end to end (these are integration tests), stub only at the *library* boundary (where our code calls into discord.py / aiohttp / yt-dlp), never a production helper that calls it. Patching a `common/utils.py` or `components/` helper bypasses the code under test and survives a prod-breaking rename.

- **Wrong:** `monkeypatch.setattr(ut, "get_role", ...)` replaces the helper itself.
- **Right:** call `ut.get_role(ut.env["ADMIN_ROLE"])`, then mutate the field you need (e.g. `.members = []`).

In addition to feature tests, **every bug fix ships with a regression test** that fails without the fix; see [Regression tests](#regression-tests) under Adding a test for the how-to.

### Immediate vs background tests

**The decision rule:**

> If I deleted everything after `invoke_slash(...)` (or `client.dispatch(...)`) returns, can my assertions still run?
> - **Yes** → `tests/immediate/`
> - **No** → `tests/background/`

**Example.** `/music play` has tests in both folders:

- `test_music_play_no_results` asserts on the "couldn't find" reply — assertions run immediately. → `immediate/`
- `test_music_play_single_song_adds_to_queue` awaits `asyncio.gather(*musicPlayer._PENDING_TASKS)` and asserts on `vc.play` being called — assertions need the background task to finish. → `background/`

### Dispatch patterns

Assert on observable behavior (response substrings, DB state, captured messages).

| Entry point | Helper | Example |
|---|---|---|
| Slash command (`@group.command`) | `invoke_slash(tree, "dota list", user, guild)` | `tests/immediate/test_dota.py` |
| Gateway event (`@client.event`) | `dpytest.message(...)` or `client.dispatch(...)` | `tests/immediate/test_emote.py` (immediate) / `tests/background/test_movie.py` (kicks off background) |
| Periodic/Async task (`PeriodicTask` / `AsyncTask`) | `@pytest.mark.looptime` + trigger (`init()` or gateway event) | `tests/background/test_dota.py` / `tests/background/test_movie.py` |
| Modal (`discord.ui.Modal`) | Instantiate modal, call `on_submit(interaction)` directly | `tests/immediate/test_movie.py` |
| Voice callback (`vc.play`'s `after=`) | Capture `after=` from `vc.play()`, invoke it | `tests/background/test_music.py` |

### Test layout

```
tests/
  conftest.py               # shared fixtures: tree, guild, members, db_dir / seeded_<feature>_db, fake_vc, client wiring
  _env_setup.py             # env + ut.guildObject bootstrap (named channels/roles)
  _factories.py             # make_<obj>() object builders + seed_<feature>_db() data
  _stubs.py                 # external-I/O stubs (HTTP, YouTube) + capturing-channel / scheduled-event patches
  _capture.py               # CapturedMessages + capturing channel/interaction
  _dispatch.py              # invoke_slash() — the slash-command test driver
  test_command_coverage.py  # guard: every registered command has a test
  immediate/                # command / modal / sync-event tests (assert right after dispatch)
  background/               # periodic & async-task tests (assert after the task runs)
```

### Adding a test

1. **Command or event?** → `tests/immediate/test_<feature>.py`. Use `invoke_slash(...)` for commands, `dpytest.message(...)`/`client.dispatch(...)` for events.
2. **Background task?** → `tests/background/test_<feature>.py`. Call `component.init()`, then `await asyncio.sleep(interval)` to trigger it.
3. **Fixing a bug?** → write it as a regression test that fails without your fix.
4. **Need test data?** → Use `seeded_<feature>_db` fixture or build state inline.
5. **Need to stub an API?** → Use helpers from `tests/_stubs.py`.

Match the structure of an existing test file: a module docstring plus `# --- … ---` separators per entry point, each named in the trigger's own vocabulary (`/cmd`, `on_event`, `@cadence`, `starter()`). The structure doubles as a per-file index of what's covered.

#### Regression tests

**Litmus:** revert the fix and run the test; if it still passes, it isn't testing the fix. Assert the invariant that broke, not an incidental symptom another code path can mask.

Mark it with a docstring starting `Regression (<commit/issue>):` and place it under the relevant entry-point separator.

Example: `tests/background/test_twitch.py::test_init_twice_cancels_the_first_task` (commit `0a4171e`: `on_ready` re-firing on reconnect stacked duplicate tasks).

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
