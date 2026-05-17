---
name: slash-command-tester
description: Use whenever code is changed that could affect the output a Discord user sees from a slash command. This includes (1) adding a new slash command, (2) modifying a slash command file in commands/, (3) modifying a component function in components/ that a slash command calls, or (4) modifying shared helpers (embed builders, common formatters) used in a slash command's call path. Confirms an integration test exists that exercises the command via tree._call, runs it, and on failure shows the diff so the user can decide whether the behavior change is intentional. If no integration test exists for the affected command, walks through writing one before running.
---

# slash-command-tester

## Before starting: verify reference files still exist

Every pattern below points at a concrete file in the codebase, not a template. Before following any sub-flow, `Read` each reference file the skill is about to suggest. If any is missing (renamed, moved, deleted), do one of:

- Find the equivalent in the current codebase. `Grep` for an unchanged distinctive string (e.g. the command name, the function signature) to locate where the pattern lives now.
- If the project has moved on from the pattern entirely (e.g., the integration-test pattern was replaced by something else), update this skill's references inline before continuing.

Don't proceed with a stale reference — the cost of a 3-second `Read` check is much smaller than the cost of duplicating an obsolete pattern.

## Purpose

The contract: every slash command is exercised end-to-end via `tree._call` from `tests/test_<feature>.py`. Whenever code in the slash command's call path changes, this skill runs the relevant integration test and branches:

- **Pass** → the change is invisible at the dispatch boundary; done.
- **Fail** → show the user the failure, let them decide: intentional behavior change (update the assertions) or bug (fix code).
- **No test yet** → write one before running.

The deeper purpose is forcing human verification before user-visible behavior changes ship. Integration tests dispatch through `tree._call` so a renamed component function, a forgotten `register_subcommand`, or a misrouted argument all surface as test failures — they can't slip through.

## When to fire

Fire on any change touching code in a slash command's call graph:

- `commands/<feature>/<name>.py` — slash command wrapper.
- `commands/admin/<feature>/<name>.py` — admin slash command wrapper.
- `components/<module>.py` — but only the functions a slash command actually calls. Most components also have event-handler and periodic paths; those have their own tests in the same `test_<feature>.py` file.
- Shared helpers in `common/utils.py` or elsewhere that flow into a slash command's output (judgment call — if `DiscordEmbedBuilder` or `send_message` changes, fire; if `async_get_request` does, probably not).

The mental test: **could a Discord user notice a difference after this change?** If yes → fire. If no → don't.

## When NOT to fire

- Event handlers and periodic tasks already have integration tests in the same `test_<feature>.py` file (e.g., `test_on_message_increments_used_emote_score`, `test_weekly_announcement_*`, `test_periodic_announces_new_live_streamer`). Changes to those paths run via the normal `./run-tests.sh tests/test_<feature>.py` flow, no special skill needed.
- Pure refactors with no output change: renaming variables, restructuring loops, changing shelve key formats. The test still passes; nothing to verify.

## Main flow

```
trigger fires

1. Identify affected slash command(s).
   For each affected slash command:

   2. Does tests/test_<feature>.py contain a test that invokes this
      command via `invoke_slash(tree, "<feature> <name>", ...)`?
        no  → go to sub-flow A: "Write a test first"
        yes → continue

   3. Run the relevant tests:
            ./run-tests.sh tests/test_<feature>.py -v
        pass → done for this command.
        fail → go to sub-flow B: "Handle drift"
```

## Sub-flow A — Write a test first

A code change affects a slash command that has no integration test. Build one before running anything. Each step below points at a real file already in the codebase to copy and adapt — there are no templates. Verify each reference file with `Read` first (see the preamble at the top of this skill).

1. **Find or create the pure function** in `components/<module>.py`. The slash command wrapper should be thin: call the pure function, send its result.
   - It MUST NOT take `discord.Interaction` or `discord.Message` as a parameter.
   - It MUST NOT call `interaction.response.send_message(...)` or `channel.send(...)` directly.
   - **Wrap the body in `try/except`** and return a context-specific error string on failure (e.g. `f"Error Printing Leaderboard: {e}"`).
   - **Copy from**: `components/dotaReplay.py:get_players_text` (no args, returns `str`) or `components/memeReview.py:get_memerboard_text` (args + guild).
   - **Swap when copying**: function name; the body; the `Error <action>:` label in the `except` clause.

2. **Write the slash command wrapper.**
   - **Public command** — copy from `commands/dota/list.py` (no params) or `commands/emote/leaderboard.py` (with `int`/`bool` defaults). Place at `commands/<feature>/<name>.py`.
   - **Admin-gated command** — copy from `commands/admin/dota/remove.py`. Place at `commands/admin/<feature>/<name>.py`. The `@discord.app_commands.checks.has_role(...)` decorator stays as-is.
   - **Swap when copying**: `name=`, `description=`, the `<module>.<pure_function>` call, the parameter signature.
   - **For new feature groups**: copy `commands/dota/__init__.py` → `commands/<feature>/__init__.py`. For admin: copy `commands/admin/dota/__init__.py` → `commands/admin/<feature>/__init__.py`. Swap only the `Group(name=..., description=...)` line.
   - **For operations >3 seconds** (YouTube lookups, external API calls): use `await interaction.response.defer()` then `await interaction.followup.send(...)`. Reference: `commands/music/play.py`.

3. **Write the test.** Copy from `tests/test_dota.py` (smallest example with both slash and periodic coverage) into `tests/test_<feature>.py` (or append a new function if the file exists).
   - Uses the shared session-scoped `tree` fixture from `tests/conftest.py` (built once via `commands.load_commands` — the same tree production uses).
   - Calls `invoke_slash(tree, "<feature> <name>", user, guild, options={...})` from `tests/_dispatch.py`.
   - Assertions are on observable behavior: response substrings (`assert "Successfully added" in msg.content`), post-condition DB state (`assert <component>.get_X("key") is not None`), captured embed fields. No snapshots.
   - **Swap when copying**: feature name, command paths, assertion substrings, fixture name (`seeded_dota_db` → `seeded_<feature>_db` or `db_dir` if no seed needed).
   - Fixtures available out of the box (`tests/conftest.py`): `tree`, `db_dir`, `guild`, `members`, `admin_member`, `regular_member`, plus feature-specific seeders (`seeded_meme_db`, `seeded_dota_db`, `seeded_twitch_db`, `seeded_emote_db`, `seeded_movie_db`).
   - Use `admin_member` for admin-gated commands (it has the ADMIN role), `regular_member` otherwise.
   - Richer references for tougher cases: `tests/test_twitch.py` (HTTP-stubbed external API), `tests/test_music.py` (voice client + YouTube API stubs), `tests/test_movie.py` (modal `on_submit` + scheduled events).

4. Run the test:

   ```
   ./run-tests.sh tests/test_<feature>.py::test_<your_new_test> -v
   ```

5. **Show the user the test output.** If it passes, the test is locked in. If it fails, ask whether the assertion is wrong or the code is.

## Sub-flow B — Handle drift (test failed)

An integration test that previously passed is now failing.

1. **Capture the failure output.** pytest's diff message shows which assertion failed: which substring is missing, which DB state is wrong, which embed field changed.

2. **Present the diff to the user.** Show:
   - What the test asserted.
   - What actually happened (from pytest's failure message — the response content, the DB state, etc.).

3. Ask the user explicitly: **"Is this behavior change intentional? (a) Yes — update the assertions. (b) No — the code has a bug; let me know what to fix."**

4. Branch:
   - **Intentional** → update the test's assertion to match the new behavior. Confirm the new assertion captures what a Discord user should see. Rerun to confirm pass.
   - **Not intentional** → leave the test alone. Help the user diagnose: which code change caused the drift, what should it have done.

## Identifying affected slash command(s) from a code change

- **`commands/<feature>/<name>.py`** → command is `<feature>` `<name>`. Test file: `tests/test_<feature>.py`.
- **`commands/admin/<feature>/<name>.py`** → admin command. Same test file pattern.
- **`components/<module>.py`** → grep for usages of the changed function(s) under `commands/`. Every slash command that imports and calls it is affected.
- **`common/utils.py`** → judgment call. If the change affects rendering used by slash commands (`DiscordEmbedBuilder`), grep `commands/` for the symbol.
- **`tests/_capture.py` / `tests/_dispatch.py` / `tests/_factories.py`** → all integration tests are affected. Run the full suite: `./run-tests.sh -v`.

If you can't tell which commands are affected, default to running the full suite. Conservative is fine — it's fast (under 2 seconds).

## Patterns for tricky cases

### Commands with discord.Member parameters

`invoke_slash` auto-detects Member-like option values (anything with `.id` and `.name` that isn't a primitive) and builds the `resolved.users` + `resolved.members` data discord.py's Namespace needs. Pass a `make_member(101, "alice")` from `tests/_factories.py` directly:

```python
alice = make_member(103, "carol", nick="Carol")
capture = await invoke_slash(tree, "admin dota add", admin_member, guild,
    options={"user": alice, "player_id": 55555})
```

### Commands that mutate module-level globals

If a command reads or writes module-level state (e.g., `musicPlayer.vc`, `dotaReplay._RECENT_MATCHES_TASK`, `twitchAnnouncement.twitch_OAuth_token`), add an autouse fixture in `tests/test_<feature>.py` that resets it before/after each test. Reference: `tests/test_music.py:fresh_music_state`, `tests/test_twitch.py:reset_twitch_module_state`.

### Commands that hit external APIs

Stub at the **library boundary**, not at production helpers:

- HTTP → patch `common.utils.async_get_request` / `async_post_request`. Reference: `tests/test_twitch.py:_stub_twitch`, `tests/test_dota.py:fake_get`.
- YouTube → patch `musicPlayer.Aiogoogle` and `musicPlayer.YoutubeDL`. Reference: `tests/test_music.py:_patch_youtube`.

Patching helpers like `_validate_twitch_username` or `process_input` directly is the old unit-test pattern — it lets renames slip through. Avoid.

### Commands that return str OR discord.Embed

Some commands branch on state. Use `commands/music/_helpers.py:send_string_or_embed` (or replicate the pattern). Tests assert against whichever shape was sent:

```python
[msg] = capture.messages
if "queue is empty" in msg.content.lower():
    ...
else:
    assert msg.embed is not None
    assert "expected text" in msg.embed["description"]
```

### Commands that send multiple messages per invocation

If the pure function returns `list[str]` (e.g. `play_song_request`), the slash command does `await interaction.response.defer()` then `for msg in messages: await interaction.followup.send(msg)`. The captured `capture.messages` is a list with one entry per `followup.send`.

### Modal-based commands

Discord modals (`discord.ui.Modal`) don't traverse the command tree. The slash command opens the modal; the user's submission lands at `Modal.on_submit(interaction)`. Tests instantiate the modal, set its `TextInput._value` fields, and call `on_submit` with a `make_capturing_interaction` directly. Reference: `tests/test_movie.py:test_movie_add_suggestion_modal_submit_adds_to_db`.

### Deterministic timestamps

Embeds with elapsed-time footers need a frozen clock. Patch the module's `datetime`:

```python
with patch("components.musicPlayer.datetime") as dt_mock:
    dt_mock.now.return_value = datetime(2024, 1, 1, 12, 0, 30)
    result = musicPlayer.build_now_playing_embed()
```

## Reference files

Copy from real production code. No templates — the codebase itself is the source of truth, so the references can't rot silently.

| Pattern | Reference file | What to swap when copying |
|---|---|---|
| Pure function (no args) | `components/dotaReplay.py:get_players_text` | function name; body; error label in `except` |
| Pure function (with args) | `components/memeReview.py:get_memerboard_text` | function name; body; parameter list; error label |
| Public slash command (no params) | `commands/dota/list.py` | `name=`, `description=`, `<module>.<pure_function>` call |
| Public slash command (with params) | `commands/emote/leaderboard.py` | same as above + parameter signature |
| Admin slash command | `commands/admin/dota/remove.py` | same as public; keep `@has_role` decorator as-is |
| `commands/<feature>/__init__.py` | `commands/dota/__init__.py` | only the `Group(name=..., description=...)` line |
| `commands/admin/<feature>/__init__.py` | `commands/admin/dota/__init__.py` | same naming swap |
| Periodic task wiring | `components/dotaReplay.py:init` | the `PeriodicTask.<factory>(...)` call + lambda body |
| Test file (slash + periodic) | `tests/test_dota.py` | feature name, command paths, assertion substrings |
| Test file (event handlers via dpytest) | `tests/test_emote.py` | same + emoji/event-payload setup |
| Test file (modal submission) | `tests/test_movie.py:test_movie_add_suggestion_modal_submit_adds_to_db` | the modal class + field values |

**Existing infrastructure** (use, don't reinvent):

- `tests/_dispatch.py` — `invoke_slash`, `run_periodic_once`.
- `tests/_capture.py` — `SentMessage`, `CapturedMessages`, `make_capturing_interaction`, `make_capturing_channel`.
- `tests/_factories.py` — `make_member`, `make_guild`, `DEFAULT_MEMBERS`, shelve seeders.
- `tests/conftest.py` — `tree` (session-scoped via `load_commands`), `db_dir`, `guild`, `admin_member`, `regular_member`, feature seeder fixtures.
- `docs/DEVELOPMENT.md` — the three integration patterns documented at the project level.
- `run-tests.sh` — Docker-based test runner.
