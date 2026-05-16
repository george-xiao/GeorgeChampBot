---
name: slash-command-tester
description: Use whenever code is changed that could affect the output a Discord user sees from a slash command. This includes (1) adding a new slash command, (2) modifying a slash command file in commands/, (3) modifying a component function in components/ that a slash command calls, or (4) modifying shared helpers (embed builders, common formatters) used in a slash command's call path. Runs the relevant snapshot tests; if they pass, done. If they fail, shows the diff and asks the user whether the change is intentional (update snapshot) or a bug (fix code). If no test exists for the affected command, walks through writing one before running. Do NOT use for event handlers (on_message, on_raw_reaction_add), background tasks (check_recent_matches, check_twitch_live, announcements), or internal refactors that don't change user-visible output.
---

# slash-command-tester

## Purpose

The contract: every slash command's user-visible output is locked into a JSON snapshot. Whenever code in the slash command's call path changes, this skill runs the snapshot tests and branches:

- **Pass** → the change is invisible to users; done.
- **Fail** → show the user the diff and let them decide: intentional change (refresh snapshot) or bug (fix code).
- **No test yet** → write one before running.
- **No snapshot yet** → capture, show, confirm, lock.

Locking is the mechanism. The deeper purpose is forcing human verification before user-visible behavior changes ship.

## When to fire

Fire on any change touching code in a slash command's call graph:

- `commands/<feature>/<name>.py` — slash command wrapper.
- `commands/admin/<feature>/<name>.py` — admin slash command wrapper.
- `components/<module>.py` — but only the functions a slash command actually calls (most components mix command logic with event handlers and background tasks).
- Shared helpers in `common/utils.py` or elsewhere that flow into a slash command's output (judgment call — if `DiscordEmbedBuilder` or `send_message` is touched, fire; if `async_get_request` is touched, probably not).

The mental test: **could a Discord user notice a difference after this change?** If yes → fire. If no → don't.

## When NOT to fire

- Event handlers: `on_message`, `on_raw_reaction_add`, `on_voice_state_update`, `on_member_join`.
- Background/periodic tasks: `check_recent_matches`, `check_twitch_live`, `announcement_task`, `best_announcement_task`, `play_song`, `check_disconnect`.
- Internal refactors with no output change: renaming variables, restructuring loops, changing shelve key formats (the visible output is the same).

## Main flow

```
trigger fires

1. Identify affected slash command(s).
   For each affected slash command:

   2. Does tests/test_<feature>.py contain a test for this command?
        no  → go to sub-flow A: "Write a test first"
        yes → continue

   3. Does tests/snapshots/<feature>/<command>.json exist?
        no  → go to sub-flow B: "Capture initial snapshot"
        yes → continue

   4. Run plain tests:
            ./run-tests.sh tests/test_<feature>.py -v
        pass → done for this command.
        fail → go to sub-flow C: "Handle drift"
```

## Sub-flow A — Write a test first

A code change affects a slash command that has no test. Before running anything, build one. Use the template files in `.claude/skills/templates/` — they're real Python files so they can't drift from current practice.

1. **Find or create the pure function** in `components/<module>.py`.
   - The slash command should call a function that takes plain args (user, guild, query, etc.) and returns a `str`, a `discord.Embed`, or a list of those.
   - It MUST NOT take `Interaction` or `Message`. It MUST NOT call `interaction.response.send_message(...)` or `channel.send(...)`.
   - **Wrap the body in `try/except`** and return a context-specific error string on failure (e.g. `f"Error Printing Leaderboard: {e}"`). Without this, unexpected exceptions hit the generic `handle_slash_command_error` admin-ping handler, which is less informative for the user. Template: `.claude/skills/templates/pure_function.py`.
   - If the existing code mixes I/O with compute, refactor: lift the rendering out into a pure function, leave the slash command to call it and pass the result to `interaction.response.send_message`.
   - Reference: `components/memeReview.py:get_memerboard_text` — `(page: int, guild) -> str`.

2. **Write the slash command wrapper.** Copy the matching template:
   - Public command: `.claude/skills/templates/slash_public.py` → `commands/<feature>/<name>.py`.
   - Admin-gated command: `.claude/skills/templates/slash_admin.py` → `commands/admin/<feature>/<name>.py`.
   - Replace the `<placeholders>` listed in the template's module docstring.
   - If this is the first command for a new feature group, also copy `templates/group_init.py` → `commands/<feature>/__init__.py` (and `templates/admin_subgroup_init.py` → `commands/admin/<feature>/__init__.py` for admin features). Auto-discovery picks up the rest.
   - If the operation can exceed 3 seconds (yt-dlp lookups, external API calls), modify the wrapper to use `await interaction.response.defer()` then `await interaction.followup.send(...)` instead of `response.send_message`.
   - Reference: `commands/admin/movie/pick_host.py`.

3. **Write the test.** Copy `.claude/skills/templates/test_skeleton.py` → `tests/test_<feature>.py` (or append a new function if the file exists). Replace the `<placeholders>` listed in the template's module docstring.
   - Fixtures available out of the box (`tests/conftest.py`): `db_dir`, `guild`, `members`, `admin_member`, `regular_member`, `snapshots_dir`, plus any feature-specific seeder (`seeded_meme_db`, `seeded_dota_db`, `seeded_twitch_db`, `seeded_emote_db`, `seeded_movie_db`).
   - If the component reads shelve state that doesn't have a seeder yet, add one to `tests/_fixtures.py` (mirror `seed_meme_leaderboard`) and expose it as a fixture in `tests/conftest.py`.
   - Use `admin_member` for admin tests, `regular_member` otherwise.
   - Reference: `tests/test_meme.py`.

4. Now jump to **sub-flow B** to capture the initial snapshot.

## Sub-flow B — Capture initial snapshot

No snapshot exists yet for this test. Run with `SNAPSHOT_UPDATE=1` to write the JSON, then **show the user the captured output** and ask if it matches intent.

1. Run:

   ```
   SNAPSHOT_UPDATE=1 ./run-tests.sh tests/test_<feature>.py -v
   ```

   This writes `tests/snapshots/<feature>/<command>.json`. The test will "pass" because update mode skips the assertion.

2. **Open the JSON and present its contents to the user** (use the Read tool to show it inline). Don't just say "snapshot written" — actually display the captured `content` and `embed` fields.

3. Ask the user explicitly: **"Does this output match what a Discord user should see when they run this command? Update the snapshot, or fix the code first?"**

4. Branch on the user's answer:
   - **Matches intent** → commit the snapshot. Done.
   - **Doesn't match** → the code or test has a bug. Fix it, return to step 1.

This step is non-skippable. `SNAPSHOT_UPDATE=1` accepts any output, including buggy output. Skipping the human eyeball locks in bugs as the regression baseline.

## Sub-flow C — Handle drift (test failed)

A locked snapshot exists; plain tests just failed. The captured output drifted from what's locked.

1. **Capture the new output** (without overwriting the locked file yet — pytest's mismatch message already shows the diff; you can also temporarily inspect by running with `SNAPSHOT_UPDATE=1` to a scratch location if needed, but usually the test output is enough).

2. **Present the diff to the user.** Show both:
   - The locked snapshot content (what the test expected).
   - The current captured content (what the code now produces).

   The diff is exactly what a Discord user would see differently after this change.

3. Ask the user explicitly: **"Is this output change intentional? (a) Yes — update the snapshot. (b) No — the code has a bug; let me know what to fix."**

4. Branch:
   - **Intentional** → run `SNAPSHOT_UPDATE=1 ./run-tests.sh tests/test_<feature>.py -v`, then re-display the new snapshot and ask one more confirmation ("the snapshot now contains the new output, does it look right?"). On yes, commit the snapshot alongside the code change. On no, return to step 1.
   - **Not intentional** → leave the snapshot untouched. Help the user diagnose: which code change caused the drift, what should it have done. Don't refresh the snapshot under any circumstances until the user explicitly confirms.

## Identifying affected slash command(s) from a code change

When the trigger fires, you need to map the changed file(s) to the slash command(s) they affect:

- **`commands/<feature>/<name>.py`** → command is `<feature>` `<name>`. Test file: `tests/test_<feature>.py`. Snapshot dir: `tests/snapshots/<feature>/`.
- **`commands/admin/<feature>/<name>.py`** → admin command. Same test file pattern.
- **`components/<module>.py`** → grep for usages of the changed function(s) under `commands/`. Every slash command that imports and calls it is affected.
- **`common/utils.py`** or shared helpers → judgment call. If the change affects formatting/rendering used by slash commands (e.g., `DiscordEmbedBuilder`), grep `commands/` for `DiscordEmbedBuilder` or whatever symbol changed.
- **`tests/_capture.py` / `tests/_fixtures.py`** → all snapshot tests are affected. Run the full suite: `./run-tests.sh -v`.

If you can't tell from a code change which commands are affected, default to running the full suite. Conservative is fine.

## Patterns for tricky cases

These surfaced during the prefix-to-slash migration. Apply when relevant.

### Commands that mutate module-level globals

If the slash command's pure function reads or writes module-level state (e.g., `musicPlayer.vc`, `musicPlayer.sq`, `musicPlayer.loop_status`), add an autouse fixture in `tests/test_<feature>.py` that resets that state before/after each test:

```python
@pytest.fixture(autouse=True)
def fresh_music_state():
    from components import musicPlayer
    musicPlayer.reset_state()
    yield
    musicPlayer.reset_state()
```

Without this, state leaks across tests and snapshots become order-dependent.

### Commands that return str OR discord.Embed

Some commands branch on state ("Queue is empty." string vs. an embed page). Use `commands/music/_helpers.py:send_string_or_embed` (or replicate the pattern) so the slash command handles both:

```python
result = await musicPlayer.queue_response_page(page)
if isinstance(result, discord.Embed):
    await interaction.response.send_message(embed=result)
else:
    await interaction.response.send_message(result)
```

Tests mirror this in the capture path.

### Commands that send multiple messages per invocation

If the pure function returns `list[str]` (e.g. `play_song_request` can emit "song limit reached" + "Added N songs"), the slash command uses `interaction.response.defer()` followed by a loop of `interaction.followup.send(msg)`. Tests do the same:

```python
for msg in messages:
    await interaction.followup.send(msg)
```

The captured snapshot is a list with one entry per message.

### Mocking external APIs

Mock at the helper-function boundary, not at the network layer. Add a private helper in the component (e.g., `_validate_twitch_username`, `process_input`) that does the network call. Tests `unittest.mock.patch` that helper:

```python
with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=True)):
    text = await twitchAnnouncement.add_streamer_to_db("alice", "alicestream", guild)
```

This is cleaner than patching `aiohttp` or `requests` at the network layer.

### Building partial fixture objects

If a domain class's `__init__` requires data from an external API (e.g., `SongItem(entry, requester)` parses a YouTube response), use `cls.__new__(cls)` to bypass the constructor and manually set attributes:

```python
def make_song_item(title="Song A", duration=180):
    song = SongItem.__new__(SongItem)
    song.title = title
    song.duration = duration
    song.start_time = None
    return song
```

This lets tests construct realistic fixtures without recreating the external dependency.

### Deterministic timestamps

Embeds with elapsed-time footers (`now_playing` shows `00:30/02:05`) need a frozen clock. Patch the module's `datetime`:

```python
with patch("components.musicPlayer.datetime") as dt_mock:
    dt_mock.now.return_value = datetime(2024, 1, 1, 12, 0, 30)
    result = musicPlayer.build_now_playing_embed()
```

Anything that calls `datetime.now()` inside the patched module now sees the fixed value.

### Passing `guild` into pure functions

Components that call `ut.get_member(name)` depend on the global `ut.guildObject`, which isn't set in tests. Refactor the pure function to take a `guild` parameter and the slash command passes `interaction.guild`. Tests pass the fixture guild. Avoid monkeypatching `ut.guildObject` — too much spooky action.

## Reference files

**Templates** (copy these as starting points):
- `.claude/skills/templates/pure_function.py` — pure function inside `components/<module>.py`.
- `.claude/skills/templates/test_skeleton.py` — new test file.
- `.claude/skills/templates/slash_public.py` — public slash command file.
- `.claude/skills/templates/slash_admin.py` — admin-gated slash command file.
- `.claude/skills/templates/group_init.py` — `commands/<feature>/__init__.py` for a new feature group.
- `.claude/skills/templates/admin_subgroup_init.py` — `commands/admin/<feature>/__init__.py` for a new admin subgroup.

**Existing infrastructure**:
- `tests/_capture.py` — `SentMessage`, `CapturedMessages`, `make_capturing_interaction`, `assert_snapshot`, mention normalization.
- `tests/_fixtures.py` — `DEFAULT_MEMBERS`, `make_guild`, `make_member`, shelve seeders.
- `tests/conftest.py` — `db_dir`, `guild`, `members`, `admin_member`, `regular_member`, `snapshots_dir`, feature seeder fixtures.
- `tests/test_meme.py` — minimal end-to-end example.
- `commands/meme/leaderboard.py` — example public slash command.
- `commands/admin/movie/pick_host.py` — example admin slash command.
- `components/memeReview.py:get_memerboard_text` — example pure function.
- `run-tests.sh` — test runner. Builds the `test` stage and runs pytest.
- `Dockerfile` — `base` / `test` / `prod` stages.
- `requirements-test.in` / `requirements-test.txt` — test deps pinned via `pip-compile --constraint=requirements.txt`.
