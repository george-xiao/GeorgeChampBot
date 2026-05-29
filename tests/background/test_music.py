"""Background tests for music
Tasks: _DISCONNECT_TAKS (3mins via musicPlayer.init())
Misc.: play_song() callback chain (for auto-playing next song)

Verifies auto-disconnect on idle, song queuing via after= callbacks, and playback lifecycle.
"""

import asyncio
from collections import deque
from unittest.mock import MagicMock

import discord
import pytest

from components import musicPlayer
from tests._dispatch import invoke_slash
from tests._factories import make_song_item
from tests._stubs import patch_bot_channel, stub_youtube

pytestmark = [pytest.mark.looptime]


@pytest.fixture(autouse=True)
def fresh_music_state():
    musicPlayer.reset_state()
    yield
    musicPlayer.reset_state()


# --- @every-3min check_disconnect ---


async def test_check_disconnect_no_vc_is_noop(monkeypatch):
    capture = patch_bot_channel(monkeypatch)

    musicPlayer.init()
    await asyncio.sleep(180)

    assert capture.messages == []


async def test_check_disconnect_alone_in_channel_eventually_disconnects(monkeypatch, fake_vc):
    """First firing arms disconnect; second firing triggers it + announces."""
    capture = patch_bot_channel(monkeypatch)
    fake_vc.channel.members = [MagicMock()]  # just the bot
    musicPlayer.vc = fake_vc
    musicPlayer.init()

    await asyncio.sleep(180)  # first firing — arms
    assert musicPlayer.should_disconnect is True
    fake_vc.disconnect.assert_not_called()
    assert capture.messages == []

    await asyncio.sleep(180)  # second firing — disconnects + announces
    fake_vc.disconnect.assert_awaited_once()
    assert [m.content for m in capture.messages] == ["Bot Disconnected."]


async def test_check_disconnect_not_alone_clears_arm(monkeypatch, fake_vc):
    """If others are in the channel and a song is playing, arm is cleared."""
    capture = patch_bot_channel(monkeypatch)
    fake_vc.channel.members = [MagicMock(), MagicMock()]
    musicPlayer.vc = fake_vc
    musicPlayer.sq.curr_song = make_song_item("Currently Playing")
    musicPlayer.should_disconnect = True  # previously armed

    musicPlayer.init()
    await asyncio.sleep(180)

    assert musicPlayer.should_disconnect is False
    fake_vc.disconnect.assert_not_called()
    assert capture.messages == []


# --- play_song lifecycle (callback chain) ---


def _make_live_vc():
    vc = MagicMock(spec=discord.VoiceClient)
    vc.is_connected.return_value = True
    vc.is_playing.return_value = False
    vc.is_paused.return_value = False
    return vc


def _capture_after_callback(vc_mock, monkeypatch):
    """Capture vc.play's after= callback so a test can simulate the song ending.

    The callback bounces the next play_song onto the loop via
    asyncio.run_coroutine_threadsafe (in prod it fires from discord's voice
    thread). We wrap that call to capture the Future it returns, so trigger can
    await the chained play_song to actual completion rather than guessing how
    many loop cycles it needs.
    """
    captured = {}
    scheduled = []

    def _fake_play(source, *, after=None):
        captured["after"] = after

    vc_mock.play = MagicMock(side_effect=_fake_play)

    real_run = asyncio.run_coroutine_threadsafe

    def _capturing_run(coro, loop):
        future = real_run(coro, loop)
        scheduled.append(future)
        return future

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", _capturing_run)

    async def trigger_song_end(error=None):
        cb = captured.get("after")
        assert cb is not None, "vc.play was not called — no after= callback captured"
        cb(error)
        while scheduled:  # await each play_song the callback scheduled
            await asyncio.wrap_future(scheduled.pop(0))

    return trigger_song_end


async def test_play_song_logs_playback_error(monkeypatch):
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()
    await trigger_end(error=Exception("ffmpeg crashed"))

    # First play_song: "Now Playing: Next Song". After callback: "Playback error" then curr_song clears.
    titles = [m.embed["title"] for m in capture.messages]
    assert titles == ["Now Playing", "Playback error"]
    assert capture.messages[0].embed["description"] == "Next Song"
    assert capture.messages[1].embed["description"] == "ffmpeg crashed"


async def test_play_song_bails_when_vc_disconnected(monkeypatch):
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    vc_mock.is_connected.return_value = False

    await trigger_end()

    assert vc_mock.play.call_count == 1
    # Only the first play_song's "Now Playing" landed; trigger_end bailed before sending.
    assert [m.embed["description"] for m in capture.messages] == ["Next Song"]


async def test_play_song_loopqueue_rotates_to_back(monkeypatch):
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 1  # LOOPQUEUE

    song_a = make_song_item("Song A")
    song_b = make_song_item("Song B")
    musicPlayer.sq.curr_song = song_a
    musicPlayer.sq.queue = deque([song_b])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song_b

    await trigger_end()

    assert musicPlayer.sq.curr_song is song_a
    assert song_b in musicPlayer.sq.queue
    assert [m.embed["description"] for m in capture.messages] == ["Song B", "Song A"]


async def test_play_song_loopsong_replays_current(monkeypatch):
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 2  # LOOPSONG

    song_a = make_song_item("Song A")
    song_b = make_song_item("Song B")
    musicPlayer.sq.curr_song = song_a
    musicPlayer.sq.queue = deque([song_b])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song_a

    await trigger_end()

    assert musicPlayer.sq.curr_song is song_a
    assert list(musicPlayer.sq.queue) == [song_b]
    assert [m.embed["description"] for m in capture.messages] == ["Song A", "Song A"]


async def test_play_song_loopsong_replays_with_empty_queue(monkeypatch):
    """Regression: empty-queue early return must not drop the looping song."""
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 2  # LOOPSONG

    song = make_song_item("Only Song")
    musicPlayer.sq.curr_song = song

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song
    vc_mock.play.assert_called_once()

    await trigger_end()

    assert musicPlayer.sq.curr_song is song
    assert vc_mock.play.call_count == 2
    assert [m.embed["description"] for m in capture.messages] == ["Only Song", "Only Song"]


async def test_play_song_loopdisabled_clears_when_queue_empty(monkeypatch):
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Final Song")
    musicPlayer.sq.queue = deque()

    await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is None
    vc_mock.play.assert_not_called()
    assert capture.messages == []


# --- /music play (background-driven) ---
# /music play replies immediately with "Added 'X'" but kicks off play_song as a tracked
# background task. The test awaits that task before asserting on its side effects.


async def test_music_play_single_song_adds_to_queue(tree, guild, music_member, fake_vc, monkeypatch):
    bot_capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch, search_video_id="abc123")
    capture = await invoke_slash(
        tree,
        "music play",
        music_member,
        guild,
        options={"query": "My Song"},
    )
    # play_song is kicked off as a tracked background task; await it to completion.
    await asyncio.gather(*musicPlayer._PENDING_TASKS)
    contents = [m.content for m in capture.messages]
    assert any("Added 'My Song'" in c for c in contents)
    # play_song ran and called vc.play (song is now playing)
    fake_vc.play.assert_called_once()
    # play_song also announced the track on botChannel.
    [now_playing] = bot_capture.messages
    assert now_playing.embed["title"] == "Now Playing"
    assert now_playing.embed["description"] == "My Song"
