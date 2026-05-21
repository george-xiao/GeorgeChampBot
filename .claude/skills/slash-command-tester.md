---
name: slash-command-tester
description: Fires when code changes could affect slash command output. Ensures that a test exists (writes one if not), runs it, and prompts on behavior drift.
---

# slash-command-tester

## When to fire

Any change touching code in a slash command's call graph:

- `commands/<feature>/<name>.py` or `commands/admin/<feature>/<name>.py`
- `components/<module>.py` — only the functions a slash command calls.
- Shared helpers that affect output (`DiscordEmbedBuilder`, `send_message`, etc.).

Mental test: **could a Discord user notice a difference after this change?** If yes → fire.

## When NOT to fire

- Event handlers and periodic tasks have their own test flow that will not be handled by this skill.
- Pure refactors with no output change: renaming variables, restructuring loops, changing shelve key formats. The test still passes; nothing to verify.

## Main flow

```
trigger fires

1. Identify affected slash command(s).
2. Does tests/test_<feature>.py contain a test that invokes this command via `invoke_slash(tree, "<feature> <name>", ...)`?
      no  → Sub-flow A
      yes → continue

3. Run the relevant tests: ./run-tests.sh tests/test_<feature>.py -v
      pass → done.
      fail → Sub-flow B
```

## Sub-flow A — Write a test first

The command has no test. Write one before proceeding.

Follow the patterns in `docs/DEVELOPMENT.md#adding-a-test` for fixtures, dispatch helpers, and stubbing rules. Use `commands/README.md` reference files for the command structure.

Key steps:
1. Ensure the slash command wrapper is thin - it calls a pure function in `components/` and sends the result. The pure function must not take `discord.Interaction` as a parameter.
2. Write the test using `invoke_slash(tree, "<path>", user, guild, options={...})`.
3. If creating a new test file, include a docstring listing what's tested and at which level (see existing test files for the format).
4. Assert on observable behavior (response substrings, DB state, embed fields).
5. Test the error path: stub the dependency to raise, assert the response contains an error string (e.g. `"Error fetching .."`). This ensures the pure function has try/except handling.
6. Run: `./run-tests.sh tests/test_<feature>.py::test_<name> -v`
7. Show the user the output. If it fails, ask whether the assertion or the code is wrong.

For tricky cases (Member params, external APIs, modals, multiple messages), check existing tests:
   `tests/test_twitch.py` - HTTP-stubbed external API
   `tests/test_music.py` - voice client + YouTube stubs, module-level state reset
   `tests/test_movie.py` - modal `on_submit`, scheduled events

If the new command introduces a dispatch pattern not in the table at `docs/DEVELOPMENT.md#dispatch-patterns`, add a row to that table. Similarly, if a new fixture or stubbing pattern is introduced, update the tables in `docs/DEVELOPMENT.md#adding-a-test`.

## Sub-flow B — Handle drift (test failed)

A previously-passing test is now failing.

1. Capture the failure output (which assertion failed, expected vs actual).
2. Show the user the diff.
3. Ask: **"Is this behavior change intentional? (a) Update assertions (b) Fix the code"**
4. Branch accordingly. If updating assertions, rerun to confirm pass.

## Identifying affected commands

- `commands/<feature>/<name>.py` -> test file: `tests/test_<feature>.py`
- `components/<module>.py` -> grep `commands/` for imports of the changed function
- `tests/_capture.py`/ `tests/_dispatch.py` / `tests/_factories.py` -> run full suite: `./run-tests.sh -v`

If unsure which commands are affected, run the full suite. It's fast (under 2 seconds).