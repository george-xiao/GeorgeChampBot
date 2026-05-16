from collections import deque
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from components import musicPlayer
from components.musicPlayer import SongItem


@pytest.fixture(autouse=True)
def fresh_music_state():
    """Reset musicPlayer globals before/after each test to avoid bleed."""
    musicPlayer.reset_state()
    yield
    musicPlayer.reset_state()


def make_song_item(title="Song A", duration=180):
    """Build a SongItem without invoking the real constructor (which needs YouTube API data)."""
    song = SongItem.__new__(SongItem)
    song.yt_url = "https://www.youtube.com/watch?v=test"
    song.song_url = "https://stream.example/test.mp3"
    song.title = title
    song.channel_title = "Test Channel"
    song.requester = "alice"
    song.duration = duration
    song.start_time = None
    return song


# --- pause ---

@pytest.mark.asyncio
async def test_music_pause_not_connected(snap_send):
    await snap_send(musicPlayer.toggle_pause(), "music/pause-not-connected")


@pytest.mark.asyncio
async def test_music_pause_when_playing(snap_send):
    vc_mock = MagicMock()
    vc_mock.is_paused.return_value = False
    musicPlayer.vc = vc_mock
    await snap_send(musicPlayer.toggle_pause(), "music/pause-while-playing")


@pytest.mark.asyncio
async def test_music_pause_when_paused(snap_send):
    vc_mock = MagicMock()
    vc_mock.is_paused.return_value = True
    musicPlayer.vc = vc_mock
    await snap_send(musicPlayer.toggle_pause(), "music/pause-while-paused")


# --- queue ---

@pytest.mark.asyncio
async def test_music_queue_empty(snap_send):
    await snap_send(musicPlayer.queue_response_page(1), "music/queue-empty")


@pytest.mark.asyncio
async def test_music_queue_with_songs(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("Song A"), make_song_item("Song B"), make_song_item("Song C")])
    await snap_send(musicPlayer.queue_response_page(1), "music/queue-with-songs")


@pytest.mark.asyncio
async def test_music_queue_page_out_of_range(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("Song A")])
    await snap_send(musicPlayer.queue_response_page(99), "music/queue-out-of-range")


# --- now-playing ---

@pytest.mark.asyncio
async def test_music_now_playing_none(snap_send):
    await snap_send(musicPlayer.build_now_playing_embed(), "music/now-playing-none")


@pytest.mark.asyncio
async def test_music_now_playing_active(snap_send):
    song = make_song_item("Some Song Title", duration=125)
    song.start_time = datetime(2024, 1, 1, 12, 0, 0)
    musicPlayer.sq.curr_song = song

    # Freeze datetime.now to make elapsed time deterministic
    with patch("components.musicPlayer.datetime") as dt_mock:
        dt_mock.now.return_value = datetime(2024, 1, 1, 12, 0, 30)
        result = musicPlayer.build_now_playing_embed()

    await snap_send(result, "music/now-playing-active")


# --- skip ---

@pytest.mark.asyncio
async def test_music_skip_no_current(snap_send):
    await snap_send(musicPlayer.skip_song(0), "music/skip-no-current")


@pytest.mark.asyncio
async def test_music_skip_current(snap_send):
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.vc = MagicMock()
    await snap_send(musicPlayer.skip_song(0), "music/skip-current")


@pytest.mark.asyncio
async def test_music_skip_queued(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("Queued Song"), make_song_item("Other")])
    await snap_send(musicPlayer.skip_song(1), "music/skip-queued")


@pytest.mark.asyncio
async def test_music_skip_out_of_range(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("Only Song")])
    await snap_send(musicPlayer.skip_song(5), "music/skip-out-of-range")


# --- clear ---

@pytest.mark.asyncio
async def test_music_clear_empty(snap_send):
    await snap_send(musicPlayer.clear_queue(), "music/clear-empty")


@pytest.mark.asyncio
async def test_music_clear_with_songs(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("X"), make_song_item("Y")])
    await snap_send(musicPlayer.clear_queue(), "music/clear-with-songs")


# --- disconnect ---

@pytest.mark.asyncio
async def test_music_disconnect_not_connected(snap_send):
    await snap_send(await musicPlayer.disconnect_voice(), "music/disconnect-not-connected")


@pytest.mark.asyncio
async def test_music_disconnect_connected(snap_send):
    vc_mock = MagicMock()
    vc_mock.disconnect = AsyncMock()
    musicPlayer.vc = vc_mock
    await snap_send(await musicPlayer.disconnect_voice(), "music/disconnect-connected")


# --- shuffle ---

@pytest.mark.asyncio
async def test_music_shuffle_empty(snap_send):
    await snap_send(musicPlayer.shuffle_queue(), "music/shuffle-empty")


@pytest.mark.asyncio
async def test_music_shuffle_with_songs(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B")])
    await snap_send(musicPlayer.shuffle_queue(), "music/shuffle-with-songs")


# --- move ---

@pytest.mark.asyncio
async def test_music_move_empty(snap_send):
    await snap_send(musicPlayer.move_song(1, 2), "music/move-empty")


@pytest.mark.asyncio
async def test_music_move_success(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B"), make_song_item("C")])
    await snap_send(musicPlayer.move_song(3, 1), "music/move-success")


@pytest.mark.asyncio
async def test_music_move_out_of_range(snap_send):
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B")])
    await snap_send(musicPlayer.move_song(5, 1), "music/move-out-of-range")


# --- loop ---

@pytest.mark.asyncio
async def test_music_loop_cycle_disabled_to_queue(snap_send):
    # State starts at 0 = LOOPDISABLED via reset_state autouse fixture
    await snap_send(musicPlayer.cycle_loop(), "music/loop-disabled-to-queue")


@pytest.mark.asyncio
async def test_music_loop_cycle_queue_to_song(snap_send):
    musicPlayer.loop_status = 1  # LOOPQUEUE
    await snap_send(musicPlayer.cycle_loop(), "music/loop-queue-to-song")


@pytest.mark.asyncio
async def test_music_loop_cycle_song_to_disabled(snap_send):
    musicPlayer.loop_status = 2  # LOOPSONG
    await snap_send(musicPlayer.cycle_loop(), "music/loop-song-to-disabled")


# --- play ---

@pytest.mark.asyncio
async def test_music_play_no_results(regular_member, snap_send):
    voice_channel = MagicMock()
    voice_channel.connect = AsyncMock(return_value=MagicMock())

    with patch("components.musicPlayer.process_input", new=AsyncMock(return_value=[])):
        messages = await musicPlayer.play_song_request(regular_member, voice_channel, "something")

    await snap_send(messages, "music/play-no-results")


@pytest.mark.asyncio
async def test_music_play_single_song(regular_member, snap_send):
    voice_channel = MagicMock()
    voice_channel.connect = AsyncMock(return_value=MagicMock())

    song = make_song_item("My Song")
    with patch("components.musicPlayer.process_input", new=AsyncMock(return_value=[song])):
        messages = await musicPlayer.play_song_request(regular_member, voice_channel, "My Song")

    await snap_send(messages, "music/play-single")


@pytest.mark.asyncio
async def test_music_play_playlist(regular_member, snap_send):
    voice_channel = MagicMock()
    voice_channel.connect = AsyncMock(return_value=MagicMock())

    songs = [make_song_item(f"Song {i}") for i in range(3)]
    with patch("components.musicPlayer.process_input", new=AsyncMock(return_value=songs)):
        messages = await musicPlayer.play_song_request(regular_member, voice_channel, "playlist url")

    await snap_send(messages, "music/play-playlist")
