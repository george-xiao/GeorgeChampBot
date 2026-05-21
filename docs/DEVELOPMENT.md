# DEVELOPMENT.md

## Getting Started

See [Setup](../README.md#setup) for environment setup. Before merging, [run the bot in Docker](../README.md#run-application-using-docker-recommended) and verify your changes behave as expected.

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
4. Push. The pre-push hook verifies lint and tests pass.

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
./run-tests.sh                          # all tests
./run-tests.sh tests/test_meme.py -v    # single feature
```

### Testing philosophy

Test at the highest level you practically can, then drop down when the layer above isn't testable:

1. **Simulate the gateway** (dpytest): Real client, real event dispatch. Used for message/reaction handlers.
2. **Call `tree._call` with a crafted payload** (`invoke_slash`): Real command routing and callbacks. Used for slash commands (dpytest doesn't support interactions).
3. **Call the entry point directly** (`run_periodic_once`, `play_song()`): Real component logic. Use when no external trigger exists (periodic tasks, voice callbacks).
4. **Call a function directly**: Last resort, loses wiring coverage. Only for pure math with no dispatch boundary (`test_periodic_task.py`).

Each level exercises less of the real stack but is sometimes the only practical option. Don't drop lower than you need to.

### Dispatch patterns

Assert on observable behavior (response substrings, DB state, captured messages) — not output snapshots.

A forgotten `register_subcommand` or missing test is caught by the [coverage guard](../tests/test_command_coverage.py).

| Entry point | Helper | Example |
|---|---|---|
| Slash command (`@group.command`) | `invoke_slash(tree, "dota list", user, guild)` | `test_dota.py` |
| Gateway event (`@client.event`) | `dpytest.message(...)` or `client.dispatch("event_name", *args)` | `test_emote.py` (dpytest) / `test_movie.py` (bare dispatch) |
| Periodic task (`PeriodicTask.*`) | `run_periodic_once(task)` after `component.init()` | `test_dota.py`, `test_twitch.py` |
| Modal (`discord.ui.Modal`) | Instantiate modal, call `on_submit(interaction)` directly | `test_movie.py` |
| Voice callback (`vc.play`'s `after=`) | Call `play_song()` directly | `test_music.py` |

### Adding a test

#### Fixtures

Tests use the production `CommandTree` built by `commands.load_commands(tree)`. The session-scoped `tree` fixture in `tests/conftest.py` constructs it once per test session.

Other shared fixtures in `tests/conftest.py` include:

| Fixture | Purpose |
|---|---|
| `tree` | Production command tree |
| `guild` / `admin_member` / `regular_member` | Test guild with members |
| `db_dir` / `seeded_<feature>_db` | Temp database, optionally pre-seeded |
| `patched_periodic_start` | Disables scheduler; drive with `run_periodic_once` |
| `ut_client_ready` / `dpytest_client` | Event loop + dpytest wiring |

#### Stubs

External I/O is stubbed at the library boundary, not at the production helper that calls it:

| Dependency | Patch target |
|---|---|
| HTTP | `common.utils.async_get_request` / `async_post_request` |
| YouTube | `musicPlayer.Aiogoogle` / `musicPlayer.YoutubeDL` |
| Voice | `MagicMock(spec=discord.VoiceClient)` |

Patching production helpers directly (e.g., `memeReview.check_meme`) lets renames slip through undetected. Stick to library-boundary stubs.

#### Common Patterns

Reference these tests for non-obvious cases:

| Pattern | Reference | Key Insight |
|---|---|---|
| `discord.Member` parms | `tests/test_dota.py:test_dota_add_success` | Pass `make_member()` directly in options; `invoke_slash` handles resolved data |
| Module-level state reset | `tests/test_music.py:fresh_music_state` | `autouse=True` fixture to reset globals if needed |
| Modal submission | `tests/test_movie.py:test_movie_add_suggestion_modal_submit_adds_to_db` | Instantiate modal, set `TextInput._value`, call `on_submit` |

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
