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

    FFmpegPCMAudio is stubbed too, so play_song does not spawn a real ffmpeg at
    the fake song url. Tests can assert on how it was built via
    musicPlayer.FFmpegPCMAudio.call_args.
    """
    captured = {}
    scheduled = []

    audio_source = MagicMock(name="FFmpegPCMAudio")
    # Default: ffmpeg still running at after= time, i.e. we stopped it deliberately.
    # Tests simulating a crash set poll.return_value to an exit code.
    audio_source.return_value._process.poll.return_value = None
    monkeypatch.setattr(musicPlayer, "FFmpegPCMAudio", audio_source)

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


async def test_play_song_reports_ffmpeg_stderr(monkeypatch):
    """Regression (ffmpeg stderr inheritance): FFmpegPCMAudio was built without a
    stderr= sink, so ffmpeg inherited the bot's fd 2 and wrote its failures (e.g.
    a 403 on an expired song url) straight to the container log. Nothing reached
    Python, so the playback-error embed could only report the exit itself.
    """
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    sink = musicPlayer.FFmpegPCMAudio.call_args.kwargs.get("stderr")
    assert sink is not None, "no stderr sink — ffmpeg would inherit the bot's fd 2"
    # discord.py only spawns its stderr reader thread when .fileno() raises;
    # a sink carrying a real fileno silently reverts to inheriting fd 2.
    assert not hasattr(sink, "fileno")

    # Stand in for discord.py's reader thread pumping ffmpeg's bytes into the sink,
    # and for ffmpeg having exited non-zero by the time after= fires.
    sink.write(b"[https @ 0x55f1] HTTP error 403 Forbidden\n")
    musicPlayer.FFmpegPCMAudio.return_value._process.poll.return_value = 1
    await trigger_end(error=Exception("FFmpeg exited with code 1. Stderr: <no stderr>"))

    error_embed = capture.messages[1].embed
    assert error_embed["title"] == "Playback error"
    assert "403 Forbidden" in error_embed["fields"][0]["value"]


async def test_play_song_reports_ffmpeg_failure_without_discord_error(monkeypatch):
    """Regression: discord.py only sets its `error` when ffmpeg is reaped before the
    final read of its stdout — a race lost about as often as it is won. Keying the
    report off `error` dropped the captured stderr on the losing side, leaving the
    same silence the sink was added to fix. The exit code is the reliable signal.
    """
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    musicPlayer.FFmpegPCMAudio.call_args.kwargs["stderr"].write(b"HTTP error 403 Forbidden\n")
    musicPlayer.FFmpegPCMAudio.return_value._process.poll.return_value = 1
    await trigger_end(error=None)  # discord.py lost the race and reported nothing

    error_embed = capture.messages[1].embed
    assert error_embed["title"] == "Playback error"
    assert error_embed["description"] == "ffmpeg exited with code 1"
    assert "403 Forbidden" in error_embed["fields"][0]["value"]


async def test_play_song_skip_reports_nothing(monkeypatch):
    """A deliberate stop (/music skip) leaves ffmpeg running until discord.py's
    cleanup, so it must not be reported as a playback failure — even though the
    sink may hold routine ffmpeg warnings from the song that just played.
    """
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    musicPlayer.FFmpegPCMAudio.call_args.kwargs["stderr"].write(b"[mp3 @ 0x1] some benign warning\n")
    await trigger_end(error=None)  # poll() stays None: process still alive

    assert "Playback error" not in [m.embed["title"] for m in capture.messages]


async def test_play_song_truncates_ffmpeg_stderr_to_embed_limit(monkeypatch):
    """A flapping stream can emit far more than Discord's 1024-char field cap;
    an oversized field would fail the send and lose the error entirely."""
    capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    trigger_end = _capture_after_callback(vc_mock, monkeypatch)

    await musicPlayer.play_song()

    sink = musicPlayer.FFmpegPCMAudio.call_args.kwargs["stderr"]
    sink.write(b"x" * 10_000)
    musicPlayer.FFmpegPCMAudio.return_value._process.poll.return_value = 1
    await trigger_end(error=None)

    field = capture.messages[1].embed["fields"][0]
    assert len(field["value"]) <= 1024


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


async def test_music_play_watch_url_adds_song(tree, guild, music_member, fake_vc, monkeypatch):
    """A watch URL is parsed to a single video and queued (process_input watch-URL branch)."""
    patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch)
    capture = await invoke_slash(
        tree, "music play", music_member, guild, options={"query": "https://youtube.com/watch?v=abc123"}
    )
    await asyncio.gather(*musicPlayer._PENDING_TASKS)
    assert any("Added 'My Song'" in m.content for m in capture.messages)


async def test_music_play_playlist_adds_songs(tree, guild, music_member, fake_vc, monkeypatch):
    """A playlist URL is paginated into videos and queued (process_input playlist branch)."""
    patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch, playlist_video_ids=["v1", "v2"])
    capture = await invoke_slash(
        tree, "music play", music_member, guild, options={"query": "https://youtube.com/playlist?list=PL123"}
    )
    await asyncio.gather(*musicPlayer._PENDING_TASKS)
    assert any("Added" in m.content for m in capture.messages)


async def test_music_play_skips_unavailable_song(tree, guild, music_member, fake_vc, monkeypatch):
    """A queued song yt-dlp can't fetch is dropped with an 'unavailable' notice (process_song)."""
    bot_capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch, search_video_id="abc123", ytdl_unavailable=True)
    await invoke_slash(tree, "music play", music_member, guild, options={"query": "My Song"})
    await asyncio.gather(*musicPlayer._PENDING_TASKS)
    assert any("unavailable" in m.content for m in bot_capture.messages)


async def test_music_play_skips_song_without_playable_format(tree, guild, music_member, fake_vc, monkeypatch):
    """A song with no playable format is dropped with a 'url couldn't be found' notice (process_song)."""
    bot_capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch, search_video_id="abc123", ytdl_info={"formats": [{"ext": "mhtml", "url": "x"}]})
    await invoke_slash(tree, "music play", music_member, guild, options={"query": "My Song"})
    await asyncio.gather(*musicPlayer._PENDING_TASKS)
    assert any("couldn't be found" in m.content for m in bot_capture.messages)
