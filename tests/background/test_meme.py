"""Background tests for meme — weekly best-of + daily reset (looptime)."""

import asyncio
import shelve

import pytest

from components import memeReview
from tests._stubs import patch_main_channel

pytestmark = [pytest.mark.looptime]


async def test_weekly_best_meme_announces_to_main_channel(seeded_meme_db, monkeypatch):
    capture = patch_main_channel(monkeypatch)

    memeReview.init()
    memeReview._RESET_LIMIT_TASK.stop()  # only test the weekly task
    await asyncio.sleep(7 * 24 * 3600)

    [msg] = capture.messages
    assert "Memer of the Week" in msg.content


async def test_weekly_best_meme_handles_no_memes(monkeypatch):
    capture = patch_main_channel(monkeypatch)

    memeReview.init()
    memeReview._RESET_LIMIT_TASK.stop()
    await asyncio.sleep(7 * 24 * 3600)

    [msg] = capture.messages
    assert "No memes" in msg.content


async def test_daily_reset_clears_daily_meme_counts(seeded_meme_db):
    with shelve.open("./database/meme_leaderboard.db", writeback=True) as db:
        db["101"] = [50, 3]

    memeReview.init()
    memeReview._BEST_ANNOUNCEMENT_TASK.stop()  # only test the daily task
    await asyncio.sleep(86400)

    with shelve.open("./database/meme_leaderboard.db") as db:
        alice_after = db["101"]
    assert alice_after[0] == 50
    assert alice_after[1] == 0
