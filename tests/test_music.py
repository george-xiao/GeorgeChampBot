from tests import _env_setup  # noqa: F401

from collections import deque
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot


@pytest.fixture(autouse=True)
def fresh_music_state():
    """Reset musicPlayer globals before each test."""
    from components import musicPlayer
    musicPlayer.reset_state()
    yield
    musicPlayer.reset_state()


def make_song_item(title="Song A", duration=180):
    """Build a minimal SongItem-like object without invoking the real constructor (which needs YouTube API data)."""
    from components.musicPlayer import SongItem
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
async def test_music_pause_not_connected(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    text = musicPlayer.toggle_pause()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "music/pause-not-connected", snapshots_dir)


@pytest.mark.asyncio
async def test_music_pause_when_playing(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    vc_mock = MagicMock()
    vc_mock.is_paused.return_value = False
    musicPlayer.vc = vc_mock

    text = musicPlayer.toggle_pause()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "music/pause-while-playing", snapshots_dir)


@pytest.mark.asyncio
async def test_music_pause_when_paused(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    vc_mock = MagicMock()
    vc_mock.is_paused.return_value = True
    musicPlayer.vc = vc_mock

    text = musicPlayer.toggle_pause()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "music/pause-while-paused", snapshots_dir)


# --- queue ---

@pytest.mark.asyncio
async def test_music_queue_empty(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    result = musicPlayer.queue_response_page(1)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    if isinstance(result, discord.Embed):
        await interaction.response.send_message(embed=result)
    else:
        await interaction.response.send_message(result)

    assert_snapshot(capture.to_normalized_list(), "music/queue-empty", snapshots_dir)


@pytest.mark.asyncio
async def test_music_queue_with_songs(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("Song A"), make_song_item("Song B"), make_song_item("Song C")])

    result = musicPlayer.queue_response_page(1)
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    if isinstance(result, discord.Embed):
        await interaction.response.send_message(embed=result)
    else:
        await interaction.response.send_message(result)

    assert_snapshot(capture.to_normalized_list(), "music/queue-with-songs", snapshots_dir)


@pytest.mark.asyncio
async def test_music_queue_page_out_of_range(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("Song A")])

    result = musicPlayer.queue_response_page(99)
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    if isinstance(result, discord.Embed):
        await interaction.response.send_message(embed=result)
    else:
        await interaction.response.send_message(result)

    assert_snapshot(capture.to_normalized_list(), "music/queue-out-of-range", snapshots_dir)


# --- now-playing ---

@pytest.mark.asyncio
async def test_music_now_playing_none(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    result = musicPlayer.build_now_playing_embed()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    if isinstance(result, discord.Embed):
        await interaction.response.send_message(embed=result)
    else:
        await interaction.response.send_message(result)

    assert_snapshot(capture.to_normalized_list(), "music/now-playing-none", snapshots_dir)


@pytest.mark.asyncio
async def test_music_now_playing_active(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    song = make_song_item("Some Song Title", duration=125)
    song.start_time = datetime(2024, 1, 1, 12, 0, 0)
    musicPlayer.sq.curr_song = song

    # Freeze datetime.now to make elapsed time deterministic
    with patch("components.musicPlayer.datetime") as dt_mock:
        dt_mock.now.return_value = datetime(2024, 1, 1, 12, 0, 30)
        result = musicPlayer.build_now_playing_embed()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    if isinstance(result, discord.Embed):
        await interaction.response.send_message(embed=result)
    else:
        await interaction.response.send_message(result)

    assert_snapshot(capture.to_normalized_list(), "music/now-playing-active", snapshots_dir)


# --- skip ---

@pytest.mark.asyncio
async def test_music_skip_no_current(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    text = musicPlayer.skip_song(0)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/skip-no-current", snapshots_dir)


@pytest.mark.asyncio
async def test_music_skip_current(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    musicPlayer.vc = MagicMock()

    text = musicPlayer.skip_song(0)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/skip-current", snapshots_dir)


@pytest.mark.asyncio
async def test_music_skip_queued(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("Queued Song"), make_song_item("Other")])

    text = musicPlayer.skip_song(1)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/skip-queued", snapshots_dir)


@pytest.mark.asyncio
async def test_music_skip_out_of_range(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("Only Song")])

    text = musicPlayer.skip_song(5)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/skip-out-of-range", snapshots_dir)


# --- clear ---

@pytest.mark.asyncio
async def test_music_clear_empty(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    text = musicPlayer.clear_queue()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/clear-empty", snapshots_dir)


@pytest.mark.asyncio
async def test_music_clear_with_songs(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("X"), make_song_item("Y")])

    text = musicPlayer.clear_queue()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/clear-with-songs", snapshots_dir)


# --- disconnect ---

@pytest.mark.asyncio
async def test_music_disconnect_not_connected(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    text = await musicPlayer.disconnect_voice()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/disconnect-not-connected", snapshots_dir)


@pytest.mark.asyncio
async def test_music_disconnect_connected(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    vc_mock = MagicMock()
    vc_mock.disconnect = AsyncMock()
    musicPlayer.vc = vc_mock

    text = await musicPlayer.disconnect_voice()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/disconnect-connected", snapshots_dir)


# --- shuffle ---

@pytest.mark.asyncio
async def test_music_shuffle_empty(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    text = musicPlayer.shuffle_queue()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/shuffle-empty", snapshots_dir)


@pytest.mark.asyncio
async def test_music_shuffle_with_songs(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B")])

    text = musicPlayer.shuffle_queue()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/shuffle-with-songs", snapshots_dir)


# --- move ---

@pytest.mark.asyncio
async def test_music_move_empty(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    text = musicPlayer.move_song(1, 2)
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/move-empty", snapshots_dir)


@pytest.mark.asyncio
async def test_music_move_success(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B"), make_song_item("C")])

    text = musicPlayer.move_song(3, 1)
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/move-success", snapshots_dir)


@pytest.mark.asyncio
async def test_music_move_out_of_range(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.sq.queue = deque([make_song_item("A"), make_song_item("B")])

    text = musicPlayer.move_song(5, 1)
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/move-out-of-range", snapshots_dir)


# --- loop ---

@pytest.mark.asyncio
async def test_music_loop_cycle_disabled_to_queue(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    # State starts at 0 = LOOPDISABLED via reset_state autouse fixture
    text = musicPlayer.cycle_loop()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/loop-disabled-to-queue", snapshots_dir)


@pytest.mark.asyncio
async def test_music_loop_cycle_queue_to_song(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.loop_status = 1  # LOOPQUEUE
    text = musicPlayer.cycle_loop()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/loop-queue-to-song", snapshots_dir)


@pytest.mark.asyncio
async def test_music_loop_cycle_song_to_disabled(guild, regular_member, snapshots_dir):
    from components import musicPlayer
    musicPlayer.loop_status = 2  # LOOPSONG
    text = musicPlayer.cycle_loop()
    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)
    assert_snapshot(capture.to_normalized_list(), "music/loop-song-to-disabled", snapshots_dir)


# --- play ---

@pytest.mark.asyncio
async def test_music_play_no_results(guild, regular_member, snapshots_dir):
    from components import musicPlayer

    voice_channel = MagicMock()
    voice_channel.connect = AsyncMock(return_value=MagicMock())

    with patch("components.musicPlayer.process_input", new=AsyncMock(return_value=[])):
        messages = await musicPlayer.play_song_request(regular_member, voice_channel, "something")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    for msg in messages:
        await interaction.followup.send(msg)
    assert_snapshot(capture.to_normalized_list(), "music/play-no-results", snapshots_dir)


@pytest.mark.asyncio
async def test_music_play_single_song(guild, regular_member, snapshots_dir):
    from components import musicPlayer

    voice_channel = MagicMock()
    voice_channel.connect = AsyncMock(return_value=MagicMock())

    song = make_song_item("My Song")
    with patch("components.musicPlayer.process_input", new=AsyncMock(return_value=[song])):
        messages = await musicPlayer.play_song_request(regular_member, voice_channel, "My Song")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    for msg in messages:
        await interaction.followup.send(msg)
    assert_snapshot(capture.to_normalized_list(), "music/play-single", snapshots_dir)


@pytest.mark.asyncio
async def test_music_play_playlist(guild, regular_member, snapshots_dir):
    from components import musicPlayer

    voice_channel = MagicMock()
    voice_channel.connect = AsyncMock(return_value=MagicMock())

    songs = [make_song_item(f"Song {i}") for i in range(3)]
    with patch("components.musicPlayer.process_input", new=AsyncMock(return_value=songs)):
        messages = await musicPlayer.play_song_request(regular_member, voice_channel, "playlist url")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    for msg in messages:
        await interaction.followup.send(msg)
    assert_snapshot(capture.to_normalized_list(), "music/play-playlist", snapshots_dir)
