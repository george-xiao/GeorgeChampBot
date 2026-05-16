"""Template for tests/test_<feature>.py.

Copy to tests/test_<feature>.py and replace the placeholders:
  <feature>          — feature name (e.g. meme, dota, twitch)
  <command>          — slash command name (e.g. leaderboard, count)
  <feature_db>       — feature shelve seeder fixture from conftest.py
                        (e.g. seeded_meme_db, seeded_dota_db).
                        Use `db_dir` directly if no seeded state is needed.
  <module>           — components module (e.g. memeReview, dotaReplay)
  <pure_function>    — pure function in the component (e.g. get_memerboard_text)
  <args>             — arguments for the pure function

The `snap_send` fixture (defined in tests/conftest.py) handles capture +
mock-interaction + snapshot assertion in one call. It accepts:
  str          → sent via interaction.response.send_message(content)
  discord.Embed → sent via interaction.response.send_message(embed=...)
  list[str]    → each element sent via interaction.followup.send(...)

Wiring (that register_subcommand for the new slash file works without errors)
is covered automatically by tests/test_slash_wiring.py — no need to add a
test for that here.

Add more test functions for additional cases (empty state, error paths, etc.)
following the same pattern.
"""

import pytest

from components import <module>


@pytest.mark.asyncio
async def test_<feature>_<command>(<feature_db>, snap_send):
    result = await <module>.<pure_function>(<args>)
    await snap_send(result, "<feature>/<command>")
