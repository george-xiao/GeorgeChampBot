"""Background tests for twitch — periodic live-stream check (looptime)."""

import asyncio

import pytest

import common.utils as ut
from components import twitchAnnouncement
from tests._capture import CapturedMessages, make_capturing_channel
from tests._stubs import stub_twitch_api

pytestmark = [pytest.mark.looptime]


@pytest.fixture(autouse=True)
def reset_twitch_module_state():
    twitchAnnouncement.twitch_OAuth_token = None
    twitchAnnouncement.twitch_curr_livestreams = {}
    yield
    twitchAnnouncement.twitch_OAuth_token = None
    twitchAnnouncement.twitch_curr_livestreams = {}


async def test_periodic_announces_new_live_streamer(seeded_twitch_db, monkeypatch):
    stub_twitch_api(monkeypatch, live_streams=[{"user_name": "alicestream", "viewer_count": 42}])
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    [msg] = capture.messages
    assert "alicestream is live" in msg.content
    assert "42 viewers" in msg.content
    assert "twitch.tv/alicestream" in msg.content


async def test_periodic_silent_when_no_one_live(seeded_twitch_db, monkeypatch):
    stub_twitch_api(monkeypatch, live_streams=[])
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    assert capture.messages == []


async def test_periodic_skips_when_no_tracked_streamers(monkeypatch):
    stub_twitch_api(monkeypatch)
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    twitchAnnouncement.init()
    await asyncio.sleep(900)

    assert capture.messages == []
