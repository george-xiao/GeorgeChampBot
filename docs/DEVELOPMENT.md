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
./run-tests.sh tests/commands/test_meme.py -v     # single feature
```

### Testing philosophy

All tests inject at the dispatch boundary (the highest practical level). The WebSocket receive/parse path (discord.py internals) is not exercised. Testing it would require a mock Discord server that stays in sync with discord.py's expected gateway payloads across versions, a maintenance cost that outweighs the benefit for this project.

- Gateway events (messages, reactions, member joins): `dpytest.message(...)` or `client.dispatch(...)`
- Slash commands: `invoke_slash(...)`. dpytest doesn't support interactions, so we built this.
- Background tasks: `@pytest.mark.looptime`. Real tasks fire via fast-forwarded asyncio time. See `tests/background/` directory.
- Voice callbacks: Capture `after=` from `vc.play()`, invoke it to trigger `_schedule_next_song` → `play_song()`.

### File conventions

- `tests/commands/test_<feature>.py`: command/event tests. `tasks_noop` is autouse via `commands/conftest.py`.
- `tests/background/test_<feature>.py`: background task tests. `@pytest.mark.looptime` at module level, `db_dir` is autouse via `background/conftest.py`.
- `tests/test_command_coverage.py`: meta-test ensuring every command has a test.

### Dispatch patterns

Assert on observable behavior (response substrings, DB state, captured messages).

A forgotten `register_subcommand` or missing test is caught by the [coverage guard](../tests/test_command_coverage.py).

| Entry point | Helper | Example |
|---|---|---|
| Slash command (`@group.command`) | `invoke_slash(tree, "dota list", user, guild)` | `tests/commands/test_dota.py` |
| Gateway event (`@client.event`) | `dpytest.message(...)` or `client.dispatch(...)` | `tests/commands/test_emote.py` / `tests/commands/test_movie.py` |
| Periodic/Async task (`PeriodicTask` / `AsyncTask`) | `@pytest.mark.looptime` + trigger (`init()` or gateway event) | `tests/background/test_dota.py` / `tests/background/test_movie.py` |
| Modal (`discord.ui.Modal`) | Instantiate modal, call `on_submit(interaction)` directly | `tests/commands/test_movie.py` |
| Voice callback (`vc.play`'s `after=`) | Capture `after=` from `vc.play()`, invoke it | `tests/background/test_music.py` |

### Adding a test

1. **Command or event?** → `tests/commands/test_<feature>.py`. Use `invoke_slash(...)` for commands, `dpytest.message(...)`/`client.dispatch(...)` for events.
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
| `tasks_noop` | Disables all background task scheduling (autouse in `commands/`) |
| `ut_client_ready` / `dpytest_client` | Event loop + dpytest wiring |

#### Stubs

External I/O is stubbed at the library boundary, not at the production helper that calls it. Centralized stubs live in `tests/_stubs.py`:

| Dependency | Stub | Patch target |
|---|---|---|
| HTTP (Dota) | `stub_dota_api(monkeypatch, ...)` | `ut.async_get_request` |
| HTTP (Twitch) | `stub_twitch_api(monkeypatch, ...)` | `ut.async_get_request` / `async_post_request` |
| YouTube + yt-dlp | `stub_youtube(monkeypatch, ...)` | `musicPlayer.Aiogoogle` / `musicPlayer.YoutubeDL` |
| Voice | `MagicMock(spec=discord.VoiceClient)` | Local fixture |

Patching production helpers directly (e.g., `memeReview.check_meme`) lets renames slip through undetected. Stick to library-boundary stubs.

#### Common Patterns

Reference these tests for non-obvious cases:

| Pattern | Reference | Key Insight |
|---|---|---|
| `discord.Member` params | `tests/commands/test_dota.py:test_dota_add_success` | Pass `make_member()` directly in options; `invoke_slash` handles resolved data |
| Module-level state reset | `tests/commands/test_music.py:fresh_music_state` | `autouse=True` fixture to reset globals if needed |
| Modal submission | `tests/commands/test_movie.py:test_movie_add_suggestion_modal_submit_adds_to_db` | Instantiate modal, set `TextInput._value`, call `on_submit` |

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
