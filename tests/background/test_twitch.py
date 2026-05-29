"""Background tests for twitch
Tasks: _LIVE_CHECK_TASK (15mins via twitchAnnouncement.init())

Verifies live-stream detection, announcement, in-place updates, the OAuth retry on failure, and silence/skip paths.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from components import twitchAnnouncement
from tests._stubs import patch_main_channel, stub_twitch_api

pytestmark = [pytest.mark.looptime]


# --- @every-15min check_twitch_live ---


async def test_periodic_announces_new_live_streamer(seeded_twitch_db, monkeypatch):
    stub_twitch_api(monkeypatch, live_streams=[{"user_name": "alicestream", "viewer_count": 42}])
    capture = patch_main_channel(monkeypatch)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    [msg] = capture.messages
    assert "alicestream is live" in msg.content
    assert "42 viewers" in msg.content
    assert "twitch.tv/alicestream" in msg.content


async def test_periodic_announcement_omits_viewer_count_when_zero(seeded_twitch_db, monkeypatch):
    """A live streamer with zero viewers is announced without a viewer count."""
    stub_twitch_api(monkeypatch, live_streams=[{"user_name": "alicestream", "viewer_count": 0}])
    capture = patch_main_channel(monkeypatch)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    [msg] = capture.messages
    assert "alicestream is live!" in msg.content
    assert "viewers" not in msg.content


async def test_init_twice_cancels_the_first_task(monkeypatch):
    """Regression (commit 0a4171e): on_ready fires on every reconnect, so init() can run twice.
    The second init() must cancel the first task — otherwise two live-check loops run
    concurrently (the original bug: duplicate Twitch checks throwing errors).

    Asserts the invariant directly, not the symptom: the announce count is misleading because the
    second fire *edits* the existing message instead of re-sending."""
    stub_twitch_api(monkeypatch)

    twitchAnnouncement.init()
    first_task = twitchAnnouncement._LIVE_CHECK_TASK.async_task

    twitchAnnouncement.init()  # simulate a second on_ready (reconnect)
    await asyncio.sleep(0)  # let the cancellation propagate

    assert first_task.cancelled()  # the first loop was stopped, leaving exactly one running


async def test_periodic_silent_when_no_one_live(seeded_twitch_db, monkeypatch):
    stub_twitch_api(monkeypatch, live_streams=[])
    capture = patch_main_channel(monkeypatch)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    assert capture.messages == []


async def test_periodic_skips_when_no_tracked_streamers(monkeypatch):
    stub_twitch_api(monkeypatch)
    capture = patch_main_channel(monkeypatch)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    assert capture.messages == []


async def test_periodic_updates_existing_livestream(seeded_twitch_db, monkeypatch):
    """A streamer already announced has their message edited in place, not re-sent."""
    stub_twitch_api(monkeypatch, live_streams=[{"user_name": "alicestream", "viewer_count": 99}])
    capture = patch_main_channel(monkeypatch)
    existing = MagicMock()
    existing.edit = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr(twitchAnnouncement, "twitch_curr_livestreams", {"alicestream": existing})

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    existing.edit.assert_awaited_once()  # updated in place
    assert capture.messages == []  # nothing newly announced


async def test_periodic_reports_error_when_twitch_unreachable(seeded_twitch_db, monkeypatch):
    """When /streams keeps failing, the OAuth retry exhausts and the error is reported to the channel."""
    stub_twitch_api(monkeypatch, streams_down=True)
    capture = patch_main_channel(monkeypatch)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    assert any("Error Obtaining Live Twitch Streamer List" in m.content for m in capture.messages)
