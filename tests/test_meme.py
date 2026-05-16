import pytest

from components import memeReview


@pytest.mark.asyncio
async def test_meme_leaderboard_default_page(seeded_meme_db, guild, snap_send):
    text = await memeReview.get_memerboard_text(1, guild)
    await snap_send(text, "meme/leaderboard-page1")


@pytest.mark.asyncio
async def test_meme_leaderboard_page_2_empty(seeded_meme_db, guild, snap_send):
    text = await memeReview.get_memerboard_text(2, guild)
    await snap_send(text, "meme/leaderboard-page2-empty")
