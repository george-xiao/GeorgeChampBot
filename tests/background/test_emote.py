"""Background tests for emote
Tasks: _ANNOUNCEMENT_TASK (weekly via emoteLeaderboard.init())

Verifies weekly leaderboard announcement content and scheduling.
"""

import asyncio

import pytest

from components import emoteLeaderboard
from tests._stubs import patch_main_channel

pytestmark = [pytest.mark.looptime]


# --- @weekly announcement_task ---


async def test_weekly_announcement_reports_used_emotes(seeded_emote_db, monkeypatch):
    emoteLeaderboard.update_counts("<:kekw:101>", 5)
    emoteLeaderboard.update_counts("<:pog:102>", 3)

    capture = patch_main_channel(monkeypatch)

    emoteLeaderboard.init()
    await asyncio.sleep(7 * 24 * 3600)

    [msg] = capture.messages
    assert "Weekly emote update" in msg.content
    assert "kekw" in msg.content
    assert "pog" in msg.content

    assert emoteLeaderboard.get_emote("kekw").w_score == 0
    assert emoteLeaderboard.get_emote("pog").w_score == 0


async def test_weekly_announcement_silent_message_when_no_activity(seeded_emote_db, monkeypatch):
    capture = patch_main_channel(monkeypatch)

    emoteLeaderboard.init()
    await asyncio.sleep(7 * 24 * 3600)

    [msg] = capture.messages
    assert "No emotes were used this week" in msg.content
