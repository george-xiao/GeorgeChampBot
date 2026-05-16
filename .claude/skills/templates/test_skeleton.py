"""Template for tests/test_<feature>.py.

Copy to tests/test_<feature>.py and replace the placeholders:
  <feature>          — feature name (e.g. meme, dota, twitch)
  <command>          — slash command name (e.g. leaderboard, count)
  <feature_db>       — feature shelve seeder fixture from conftest.py
                        (e.g. seeded_meme_db, seeded_dota_db)
                        Use `db_dir` directly if no seeded state is needed.
  <module>           — components module (e.g. memeReview, dotaReplay)
  <pure_function>    — pure function in the component (e.g. get_memerboard_text)
  <args>             — arguments for the pure function

Add more test functions for additional cases (empty state, error paths, etc.)
following the same pattern.
"""

from tests import _env_setup  # noqa: F401

import pytest

from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot


@pytest.mark.asyncio
async def test_<feature>_<command>(<feature_db>, guild, regular_member, snapshots_dir):
    from components import <module>
    result = await <module>.<pure_function>(<args>)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(result)  # or embed=result

    assert_snapshot(capture.to_normalized_list(), "<feature>/<command>", snapshots_dir)
