"""Background tests for emote — weekly announcement (looptime)."""

import asyncio

import pytest

import common.utils as ut
from components import emoteLeaderboard
from tests._capture import CapturedMessages, make_capturing_channel

pytestmark = [pytest.mark.looptime]


async def test_weekly_announcement_reports_used_emotes(seeded_emote_db, monkeypatch):
    emoteLeaderboard.update_counts("<:kekw:101>", 5)
    emoteLeaderboard.update_counts("<:pog:102>", 3)

    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    emoteLeaderboard.init()
    await asyncio.sleep(7 * 24 * 3600)

    [msg] = capture.messages
    assert "Weekly emote update" in msg.content
    assert "kekw" in msg.content
    assert "pog" in msg.content

    assert emoteLeaderboard.get_emote("kekw").w_score == 0
    assert emoteLeaderboard.get_emote("pog").w_score == 0


async def test_weekly_announcement_silent_message_when_no_activity(seeded_emote_db, monkeypatch):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    emoteLeaderboard.init()
    await asyncio.sleep(7 * 24 * 3600)

    [msg] = capture.messages
    assert "No emotes were used this week" in msg.content
