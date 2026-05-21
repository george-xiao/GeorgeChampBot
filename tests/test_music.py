"""Tests for music.

- Slash commands (`/music *`) dispatch through `tree._call`.
- The `play_song` lifecycle tests (LOOPQUEUE rotation, LOOPSONG replay,
  disconnect race) call `play_song()` directly — that's the entry point
  triggered by `vc.play`'s `after=` callback when a track ends. It's
  the dispatch boundary for "song ended", just like a slash dispatch is
  the boundary for "user invoked /skip".
- `on_voice_state_update` dispatches through the production handler in
  `GeorgeChampBot.py` via `ut.client.dispatch`.
- The 3-min `check_disconnect` periodic task dispatches via
  `run_periodic_once` on the task `musicPlayer.init()` wires up.

External I/O stubbed at the library boundary:
- `musicPlayer.YoutubeDL` (yt-dlp) for `process_song`.
- `musicPlayer.Aiogoogle` (YouTube Data API) for `process_input`.
- `discord.VoiceClient` for vc.play / vc.pause / vc.disconnect.
"""

import asyncio
from collections import deque
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from components import musicPlayer
from components.musicPlayer import SongItem
from tests._dispatch import invoke_slash, run_periodic_once


# --- Fixtures ---


@pytest.fixture(autouse=True)
def fresh_music_state():
    musicPlayer.reset_state()
    yield
    musicPlayer.reset_state()


@pytest.fixture
def voice_channel():
    channel = MagicMock()
    channel.id = 5555
    channel.members = []
    return channel


@pytest.fixture
def fake_vc(voice_channel):
    vc = MagicMock(spec=discord.VoiceClient)
    vc.channel = voice_channel
    vc.is_paused.return_value = False
    vc.is_playing.return_value = False
    vc.is_connected.return_value = True
    vc.disconnect = AsyncMock()
    vc.stop = MagicMock()
    vc.pause = MagicMock()
    vc.resume = MagicMock()
    vc.play = MagicMock()
    voice_channel.connect = AsyncMock(return_value=vc)
    return vc


@pytest.fixture
def music_member(regular_member, voice_channel):
    """`regular_member` (alice) with .voice.channel set so
    `require_voice` passes. The `spec=discord.Member` it inherits from
    `make_member` lets the isinstance check inside require_voice
    accept the mock."""
    regular_member.voice = MagicMock()
    regular_member.voice.channel = voice_channel
    return regular_member


@pytest.fixture
def stubbed_bot(monkeypatch):
    """require_voice does a 'same voice channel as bot' check when both
    musicPlayer.vc and ut.botObject are set. Setting botObject=None bypasses
    the inner check so a vc-set test can still pass require_voice."""
    monkeypatch.setattr(ut, "botObject", None)


@pytest.fixture
def bot_channel_stub(monkeypatch):
    """Many code paths log to ut.botChannel.send. Replace with an AsyncMock
    that just swallows calls."""
    channel = MagicMock()
    channel.send = AsyncMock()
    monkeypatch.setattr(ut, "botChannel", channel)
    return channel


def _patch_youtube(monkeypatch, *, search_video_id=None, video_meta=None, ytdl_info=None):
    """Stub the YouTube API and yt-dlp at the library boundary.

    search_video_id: the video ID returned for a search query (None = no result).
    video_meta: the videos.list response item to wrap in a SongItem.
    ytdl_info: the dict yt-dlp's extract_info returns (default has a valid mp3 format).
    """

    class _Request:
        def __init__(self, kind):
            self.kind = kind

    class _Resource:
        def __init__(self, kind):
            self._kind = kind

        def list(self, **kwargs):
            return _Request(self._kind)

    class _Youtube:
        search = _Resource("search")
        videos = _Resource("videos")
        playlistItems = _Resource("playlistItems")

    default_meta = {
        "id": search_video_id or "abc123",
        "snippet": {"title": "My Song", "channelTitle": "Test Channel"},
        "contentDetails": {"duration": "PT3M0S"},
    }

    class _FakeAiogoogle:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def discover(self, *args, **kwargs):
            return _Youtube()

        async def as_api_key(self, request):
            if request.kind == "search":
                if search_video_id:
                    return {"items": [{"id": {"videoId": search_video_id}}]}
                return {"items": []}
            if request.kind == "videos":
                return {"items": [video_meta or default_meta]}
            return {"items": []}

    monkeypatch.setattr(musicPlayer, "Aiogoogle", _FakeAiogoogle)

    class _FakeYDL:
        def __init__(self, opts):
            pass

        def extract_info(self, url, download=False):
            return ytdl_info or {"formats": [{"ext": "mp3", "url": "https://stream.example/test.mp3"}]}

    monkeypatch.setattr(musicPlayer, "YoutubeDL", _FakeYDL)


def make_song_item(title="Song A", duration=180):
    """Build a SongItem without invoking its real (API-driven) constructor."""
    song = SongItem.__new__(SongItem)
    song.yt_url = "https://www.youtube.com/watch?v=test"
    song.song_url = "https://stream.example/test.mp3"
    song.title = title
    song.channel_title = "Test Channel"
    song.requester = "alice"
    song.duration = duration
    song.start_time = None
    return song


# === Slash command tests ===

# --- /music pause ---


async def test_music_pause_not_connected(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music pause", music_member, guild)
    [msg] = capture.messages
    assert "not playing" in msg.content.lower()


async def test_music_pause_when_playing(tree, guild, music_member, fake_vc, stubbed_bot):
    musicPlayer.vc = fake_vc
    fake_vc.is_paused.return_value = False
    capture = await invoke_slash(tree, "music pause", music_member, guild)
    [msg] = capture.messages
    assert "paused" in msg.content.lower()
    fake_vc.pause.assert_called_once()


async def test_music_pause_when_paused(tree, guild, music_member, fake_vc, stubbed_bot):
    musicPlayer.vc = fake_vc
    fake_vc.is_paused.return_value = True
    capture = await invoke_slash(tree, "music pause", music_member, guild)
    [msg] = capture.messages
    assert "resumed" in msg.content.lower()
    fake_vc.resume.assert_called_once()


# --- /music queue ---


async def test_music_queue_empty(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music queue", music_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.embed["description"].lower()


async def test_music_queue_with_songs(tree, guild, music_member, stubbed_bot):
    musicPlayer.sq.queue = deque([make_song_item("Song A"), make_song_item("Song B"), make_song_item("Song C")])
    capture = await invoke_slash(tree, "music queue", music_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    desc = msg.embed["description"]
    assert "Song A" in desc
    assert "Song B" in desc
    assert "Song C" in desc


async def test_music_queue_page_out_of_range(tree, guild, music_member, stubbed_bot):
    musicPlayer.sq.queue = deque([make_song_item("Song A")])
    capture = await invoke_slash(
        tree,
        "music queue",
        music_member,
        guild,
        options={"page": 99},
    )
    [msg] = capture.messages
    assert "out of range" in msg.embed["description"].lower()


# --- /music now-playing ---


async def test_music_now_playing_none(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music now-playing", music_member, guild)
    [msg] = capture.messages
    assert "no songs playing" in msg.embed["description"].lower()


async def test_music_now_playing_active(tree, guild, music_member, stubbed_bot):
    song = make_song_item("Some Song Title", duration=125)
    song.start_time = datetime(2024, 1, 1, 12, 0, 0)
    musicPlayer.sq.curr_song = song
    with patch("components.musicPlayer.datetime") as dt_mock:
        dt_mock.now.return_value = datetime(2024, 1, 1, 12, 0, 30)
        capture = await invoke_slash(tree, "music now-playing", music_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    assert "Some Song Title" in msg.embed["description"]


# --- /music skip ---


async def test_music_skip_no_current(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music skip", music_member, guild)
    [msg] = capture.messages
    assert "no songs playing" in msg.content.lower()


async def test_music_skip_current(tree, guild, music_member, fake_vc, stubbed_bot):
    musicPlayer.vc = fake_vc
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    capture = await invoke_slash(tree, "music skip", music_member, guild)
    [msg] = capture.messages
    assert "skipped" in msg.content.lower()
    assert "Current Song" in msg.content
    fake_vc.stop.assert_called_once()


async def test_music_skip_queued(tree, guild, music_member, stubbed_bot):
    other = make_song_item("Other")
    musicPlayer.sq.queue = deque([make_song_item("Queued Song"), other])
    capture = await invoke_slash(
        tree,
        "music skip",
        music_member,
        guild,
        options={"song_num": 1},
    )
    [msg] = capture.messages
    assert "Queued Song" in msg.content
    assert list(musicPlayer.sq.queue) == [other]


async def test_music_skip_out_of_range(tree, guild, music_member, stubbed_bot):
    musicPlayer.sq.queue = deque([make_song_item("Only Song")])
    capture = await invoke_slash(
        tree,
        "music skip",
        music_member,
        guild,
        options={"song_num": 5},
    )
    [msg] = capture.messages
    assert "between" in msg.content.lower()


# --- /music clear ---


async def test_music_clear_empty(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music clear", music_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_music_clear_with_songs(tree, guild, music_member, stubbed_bot):
    musicPlayer.sq.queue = deque([make_song_item("X"), make_song_item("Y")])
    capture = await invoke_slash(tree, "music clear", music_member, guild)
    [msg] = capture.messages
    assert "cleared" in msg.content.lower()
    assert list(musicPlayer.sq.queue) == []


# --- /music disconnect ---


async def test_music_disconnect_not_connected(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music disconnect", music_member, guild)
    [msg] = capture.messages
    assert "already disconnected" in msg.content.lower()


async def test_music_disconnect_connected(tree, guild, music_member, fake_vc, stubbed_bot):
    musicPlayer.vc = fake_vc
    capture = await invoke_slash(tree, "music disconnect", music_member, guild)
    [msg] = capture.messages
    assert "disconnected" in msg.content.lower()
    fake_vc.disconnect.assert_awaited_once()


# --- /music shuffle ---


async def test_music_shuffle_empty(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music shuffle", music_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_music_shuffle_with_songs(tree, guild, music_member, stubbed_bot, monkeypatch):
    queue = deque([make_song_item("A"), make_song_item("B")])
    musicPlayer.sq.queue = queue
    shuffle_mock = MagicMock()
    monkeypatch.setattr(musicPlayer.random, "shuffle", shuffle_mock)
    capture = await invoke_slash(tree, "music shuffle", music_member, guild)
    [msg] = capture.messages
    assert "shuffled" in msg.content.lower()
    shuffle_mock.assert_called_once_with(queue)


# --- /music move ---


async def test_music_move_empty(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(
        tree,
        "music move",
        music_member,
        guild,
        options={"move_from": 1, "move_to": 2},
    )
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_music_move_success(tree, guild, music_member, stubbed_bot):
    a, b, c = make_song_item("A"), make_song_item("B"), make_song_item("C")
    musicPlayer.sq.queue = deque([a, b, c])
    capture = await invoke_slash(
        tree,
        "music move",
        music_member,
        guild,
        options={"move_from": 3, "move_to": 1},
    )
    [msg] = capture.messages
    assert "moved" in msg.content.lower()
    assert list(musicPlayer.sq.queue) == [c, a, b]


async def test_music_move_out_of_range(tree, guild, music_member, stubbed_bot):
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B")])
    capture = await invoke_slash(
        tree,
        "music move",
        music_member,
        guild,
        options={"move_from": 5, "move_to": 1},
    )
    [msg] = capture.messages
    assert "between" in msg.content.lower()


# --- /music loop ---


async def test_music_loop_disabled_to_queue(tree, guild, music_member, stubbed_bot):
    capture = await invoke_slash(tree, "music loop", music_member, guild)
    [msg] = capture.messages
    assert "looped queue" in msg.content.lower()
    assert musicPlayer.loop_status == 1


async def test_music_loop_queue_to_song(tree, guild, music_member, stubbed_bot):
    musicPlayer.loop_status = 1
    capture = await invoke_slash(tree, "music loop", music_member, guild)
    [msg] = capture.messages
    assert "looped song" in msg.content.lower()
    assert musicPlayer.loop_status == 2


async def test_music_loop_song_to_disabled(tree, guild, music_member, stubbed_bot):
    musicPlayer.loop_status = 2
    capture = await invoke_slash(tree, "music loop", music_member, guild)
    [msg] = capture.messages
    assert "disabled loop" in msg.content.lower()
    assert musicPlayer.loop_status == 0


# --- /music play ---


async def test_music_play_no_results(tree, guild, music_member, fake_vc, stubbed_bot, bot_channel_stub, monkeypatch):
    # Search returns no video → process_input returns [].
    _patch_youtube(monkeypatch, search_video_id=None)
    monkeypatch.setattr(musicPlayer, "play_song", AsyncMock())  # don't actually play
    capture = await invoke_slash(
        tree,
        "music play",
        music_member,
        guild,
        options={"query": "nothing"},
    )
    contents = [m.content for m in capture.messages]
    assert any("couldn't find" in c.lower() for c in contents)


async def test_music_play_single_song_adds_to_queue(
    tree, guild, music_member, fake_vc, stubbed_bot, bot_channel_stub, monkeypatch
):
    _patch_youtube(monkeypatch, search_video_id="abc123")
    monkeypatch.setattr(musicPlayer, "play_song", AsyncMock())
    capture = await invoke_slash(
        tree,
        "music play",
        music_member,
        guild,
        options={"query": "My Song"},
    )
    contents = [m.content for m in capture.messages]
    assert any("Added 'My Song'" in c for c in contents)
    assert len(musicPlayer.sq.queue) == 1
    assert musicPlayer.sq.queue[0].title == "My Song"


# === on_voice_state_update ===


async def test_on_voice_state_update_resets_when_bot_disconnects(monkeypatch, fake_vc, ut_client_ready):
    """When the bot's own voice state moves from connected → disconnected,
    the on_voice_state_update handler calls musicPlayer.reset_state()."""
    bot = MagicMock()
    monkeypatch.setattr(ut, "botObject", bot)
    musicPlayer.vc = fake_vc
    musicPlayer.sq.queue = deque([make_song_item("X")])

    before = MagicMock()
    before.channel = MagicMock()
    after = MagicMock()
    after.channel = None

    ut_client_ready.dispatch("voice_state_update", bot, before, after)
    await asyncio.sleep(0)

    assert musicPlayer.vc is None
    assert list(musicPlayer.sq.queue) == []


# === Periodic: check_disconnect ===


async def test_check_disconnect_no_vc_is_noop(patched_periodic_start, bot_channel_stub):
    musicPlayer.init()
    await run_periodic_once(musicPlayer._DISCONNECT_TASK)
    assert bot_channel_stub.send.await_count == 0


async def test_check_disconnect_alone_in_channel_eventually_disconnects(
    patched_periodic_start, bot_channel_stub, fake_vc
):
    """First run flips should_disconnect to True; second run actually disconnects."""
    fake_vc.channel.members = [MagicMock()]  # just the bot
    musicPlayer.vc = fake_vc
    musicPlayer.init()

    await run_periodic_once(musicPlayer._DISCONNECT_TASK)
    # First pass arms the disconnect; bot still connected.
    assert musicPlayer.should_disconnect is True
    fake_vc.disconnect.assert_not_called()

    await run_periodic_once(musicPlayer._DISCONNECT_TASK)
    # Second pass triggers it.
    fake_vc.disconnect.assert_awaited_once()


async def test_check_disconnect_not_alone_clears_arm(patched_periodic_start, bot_channel_stub, fake_vc):
    """If the queue is playing and others are in the channel, should_disconnect stays False."""
    fake_vc.channel.members = [MagicMock(), MagicMock()]
    musicPlayer.vc = fake_vc
    musicPlayer.sq.curr_song = make_song_item("Currently Playing")
    musicPlayer.should_disconnect = True  # previously armed

    musicPlayer.init()
    await run_periodic_once(musicPlayer._DISCONNECT_TASK)

    assert musicPlayer.should_disconnect is False
    fake_vc.disconnect.assert_not_called()


# === play_song lifecycle ===
# play_song is invoked by vc.play's after= callback when a track ends. We
# invoke it directly here — that callback is the entry point, just as
# tree._call is the entry point for slash commands.


def _make_live_vc():
    vc = MagicMock(spec=discord.VoiceClient)
    vc.is_connected.return_value = True
    vc.is_playing.return_value = False
    vc.is_paused.return_value = False
    return vc


async def test_play_song_logs_playback_error(bot_channel_stub):
    await musicPlayer.play_song(playback_error=Exception("ffmpeg crashed"))
    error_call = next(c for c in bot_channel_stub.send.await_args_list if "embed" in c.kwargs)
    embed = error_call.kwargs["embed"]
    assert embed.title == "Playback error"
    assert embed.description == "ffmpeg crashed"


async def test_play_song_bails_when_vc_disconnected(bot_channel_stub):
    vc_mock = _make_live_vc()
    vc_mock.is_connected.return_value = False
    musicPlayer.vc = vc_mock
    musicPlayer.sq.queue = deque([make_song_item("Next Song")])

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    vc_mock.play.assert_not_called()


async def test_play_song_loopqueue_rotates_to_back(bot_channel_stub):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 1  # LOOPQUEUE

    song_a = make_song_item("Song A")
    song_b = make_song_item("Song B")
    musicPlayer.sq.curr_song = song_a
    musicPlayer.sq.queue = deque([song_b])

    with (
        patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)),
        patch("components.musicPlayer.FFmpegPCMAudio"),
    ):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song_b
    assert list(musicPlayer.sq.queue) == [song_a]


async def test_play_song_loopsong_replays_current(bot_channel_stub):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 2  # LOOPSONG

    song_a = make_song_item("Song A")
    song_b = make_song_item("Song B")
    musicPlayer.sq.curr_song = song_a
    musicPlayer.sq.queue = deque([song_b])

    with (
        patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)),
        patch("components.musicPlayer.FFmpegPCMAudio"),
    ):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song_a
    assert list(musicPlayer.sq.queue) == [song_b]


async def test_play_song_loopsong_replays_with_empty_queue(bot_channel_stub):
    """Regression: previously the empty-queue early return fired before the
    loop re-append, dropping the only song instead of looping it."""
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.loop_status = 2  # LOOPSONG

    song = make_song_item("Only Song")
    musicPlayer.sq.curr_song = song

    with (
        patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)),
        patch("components.musicPlayer.FFmpegPCMAudio"),
    ):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is song
    vc_mock.play.assert_called_once()


async def test_play_song_loopdisabled_clears_when_queue_empty(bot_channel_stub):
    vc_mock = _make_live_vc()
    musicPlayer.vc = vc_mock
    musicPlayer.sq.curr_song = make_song_item("Final Song")

    with patch("components.musicPlayer.process_song", new=AsyncMock(return_value=True)):
        await musicPlayer.play_song()

    assert musicPlayer.sq.curr_song is None
    vc_mock.play.assert_not_called()
