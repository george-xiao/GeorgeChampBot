"""Background tests for music — check_disconnect periodic task + play_song callback chain (looptime)."""

import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import common.utils as ut
from components import musicPlayer
from components.musicPlayer import SongItem

pytestmark = [pytest.mark.looptime]


@pytest.fixture(autouse=True)
def fresh_music_state():
    musicPlayer.reset_state()


@pytest.fixture
def bot_channel_stub(monkeypatch):
    channel = MagicMock()
    channel.send = AsyncMock()
    monkeypatch.setattr(ut, "botChannel", channel)
    return channel


@pytest.fixture
def fake_vc():
    vc = MagicMock(spec=discord.VoiceClient)
    vc.is_connected.return_value = True
    vc.is_playing.return_value = False
    vc.is_paused.return_value = False
    vc.disconnect = AsyncMock()
    vc.stop = MagicMock()
    vc.channel = MagicMock()
    vc.channel.members = [MagicMock(), MagicMock()]
    return vc


def make_song_item(title="Song A", duration=180):
    song = SongItem.__new__(SongItem)
    song.yt_url = "https://www.youtube.com/watch?v=test"
    song.song_url = "https://stream.example/test.mp3"
    song.title = title
    song.channel_title = "Test Channel"
    song.requester = "alice"
    song.duration = duration
    song.start_time = None
    return song


# === Periodic: check_disconnect ===


async def test_check_disconnect_no_vc_is_noop(bot_channel_stub):
    musicPlayer.init()
    await asyncio.sleep(180)
    assert bot_channel_stub.send.await_count == 0


async def test_check_disconnect_alone_in_channel_eventually_disconnects(bot_channel_stub, fake_vc):
    """First firing arms disconnect; second firing triggers it."""
    fake_vc.channel.members = [MagicMock()]  # just the bot
    musicPlayer.vc = fake_vc
    musicPlayer.init()

    await asyncio.sleep(180)  # first firing — arms
    assert musicPlayer.should_disconnect is True
    fake_vc.disconnect.assert_not_called()

    await asyncio.sleep(180)  # second firing — disconnects
    fake_vc.disconnect.assert_awaited_once()


async def test_check_disconnect_not_alone_clears_arm(bot_channel_stub, fake_vc):
    """If others are in the channel and a song is playing, arm is cleared."""
    fake_vc.channel.members = [MagicMock(), MagicMock()]
    musicPlayer.vc = fake_vc
    musicPlayer.sq.curr_song = make_song_item("Currently Playing")
    musicPlayer.should_disconnect = True  # previously armed

    musicPlayer.init()
    await asyncio.sleep(180)

    assert musicPlayer.should_disconnect is False
    fake_vc.disconnect.assert_not_called()


# === play_song lifecycle (callback chain) ===


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


async def test_play_song_logs_playback_error(bot_channel_stub, monkeypatch):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await trigger_end(error=Exception("ffmpeg crashed"))

    error_embeds = [
        c.kwargs["embed"]
        for c in bot_channel_stub.send.await_args_list
        if "embed" in c.kwargs and c.kwargs["embed"].title == "Playback error"
    ]
    assert len(error_embeds) == 1
    assert error_embeds[0].description == "ffmpeg crashed"


async def test_play_song_bails_when_vc_disconnected(bot_channel_stub, monkeypatch):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    vc_mock.is_connected.return_value = False

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await trigger_end()

    assert vc_mock.play.call_count == 1


async def test_play_song_loopqueue_rotates_to_back(bot_channel_stub, monkeypatch):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 1  # LOOPQUEUE

    song_a = make_song_item("Song A")
    song_b = make_song_item("Song B")
    musicPlayer.sq.curr_song = song_a
    musicPlayer.sq.queue = deque([song_b])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song_b

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await trigger_end()

    assert musicPlayer.sq.curr_song is song_a
    assert song_b in musicPlayer.sq.queue


async def test_play_song_loopsong_replays_current(bot_channel_stub, monkeypatch):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 2  # LOOPSONG

    song_a = make_song_item("Song A")
    song_b = make_song_item("Song B")
    musicPlayer.sq.curr_song = song_a
    musicPlayer.sq.queue = deque([song_b])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song_a

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await trigger_end()

    assert musicPlayer.sq.curr_song is song_a
    assert list(musicPlayer.sq.queue) == [song_b]


async def test_play_song_loopsong_replays_with_empty_queue(bot_channel_stub, monkeypatch):
    """Regression: empty-queue early return must not drop the looping song."""
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 2  # LOOPSONG

    song = make_song_item("Only Song")
    musicPlayer.sq.curr_song = song

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song
    vc_mock.play.assert_called_once()

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await trigger_end()

    assert musicPlayer.sq.curr_song is song
    assert vc_mock.play.call_count == 2


async def test_play_song_loopdisabled_clears_when_queue_empty(bot_channel_stub, monkeypatch):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Final Song")
    musicPlayer.sq.queue = deque()

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is None
    vc_mock.play.assert_not_called()
