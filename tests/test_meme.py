from tests import _env_setup  # noqa: F401

import pytest

from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot


@pytest.mark.asyncio
async def test_meme_leaderboard_default_page(seeded_meme_db, guild, regular_member, snapshots_dir):
    from components import memeReview
    text = await memeReview.get_memerboard_text(1, guild)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "meme/leaderboard-page1", snapshots_dir)


@pytest.mark.asyncio
async def test_meme_leaderboard_page_2_empty(seeded_meme_db, guild, regular_member, snapshots_dir):
    from components import memeReview
    text = await memeReview.get_memerboard_text(2, guild)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "meme/leaderboard-page2-empty", snapshots_dir)
