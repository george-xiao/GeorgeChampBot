"""Tests for music slash commands + on_voice_state_update (background: tests/background/test_music.py)."""

import asyncio
from collections import deque
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import common.utils as ut
from components import musicPlayer
from tests._dispatch import invoke_slash
from tests._factories import make_song_item
from tests._stubs import patch_bot_channel, stub_youtube


@pytest.fixture(autouse=True)
def fresh_music_state():
    musicPlayer.reset_state()
    yield
    musicPlayer.reset_state()


# --- /music play ---
# require_voice is a shared guard on every /music command; exercised here via /play.


async def test_music_play_requires_user_in_voice_channel(tree, guild, regular_member):
    regular_member.voice = None  # caller not in any voice channel
    capture = await invoke_slash(tree, "music play", regular_member, guild, options={"query": "anything"})
    [msg] = capture.messages
    assert "enter a voice channel" in msg.content.lower()


async def test_music_play_requires_same_voice_channel_as_bot(tree, guild, music_member, fake_vc, monkeypatch):
    musicPlayer.vc = fake_vc  # bot is connected somewhere
    bot_obj = MagicMock()
    bot_obj.voice.channel = MagicMock()  # ...a different channel than the caller's
    monkeypatch.setattr(ut, "botObject", bot_obj)

    capture = await invoke_slash(tree, "music play", music_member, guild, options={"query": "anything"})
    [msg] = capture.messages
    assert "same voice channel as the bot" in msg.content.lower()


async def test_music_play_no_results(tree, guild, music_member, fake_vc, monkeypatch):
    # Search returns no video → process_input returns [].
    bot_capture = patch_bot_channel(monkeypatch)
    stub_youtube(monkeypatch, search_video_id=None)
    capture = await invoke_slash(
        tree,
        "music play",
        music_member,
        guild,
        options={"query": "nothing"},
    )
    contents = [m.content for m in capture.messages]
    assert any("couldn't find" in c.lower() for c in contents)
    assert bot_capture.messages == []  # nothing goes to botChannel on the no-results path


# --- /music pause ---


async def test_music_pause_not_connected(tree, guild, music_member):
    capture = await invoke_slash(tree, "music pause", music_member, guild)
    [msg] = capture.messages
    assert "not playing" in msg.content.lower()


async def test_music_pause_when_playing(tree, guild, music_member, fake_vc):
    musicPlayer.vc = fake_vc
    fake_vc.is_paused.return_value = False
    capture = await invoke_slash(tree, "music pause", music_member, guild)
    [msg] = capture.messages
    assert "paused" in msg.content.lower()
    fake_vc.pause.assert_called_once()


async def test_music_pause_when_paused(tree, guild, music_member, fake_vc):
    musicPlayer.vc = fake_vc
    fake_vc.is_paused.return_value = True
    capture = await invoke_slash(tree, "music pause", music_member, guild)
    [msg] = capture.messages
    assert "resumed" in msg.content.lower()
    fake_vc.resume.assert_called_once()


# --- /music queue ---


async def test_music_queue_empty(tree, guild, music_member):
    capture = await invoke_slash(tree, "music queue", music_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.embed["description"].lower()


async def test_music_queue_with_songs(tree, guild, music_member):
    musicPlayer.sq.queue = deque([make_song_item("Song A"), make_song_item("Song B"), make_song_item("Song C")])
    capture = await invoke_slash(tree, "music queue", music_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    desc = msg.embed["description"]
    assert "Song A" in desc
    assert "Song B" in desc
    assert "Song C" in desc


async def test_music_queue_page_out_of_range(tree, guild, music_member):
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


async def test_music_now_playing_none(tree, guild, music_member):
    capture = await invoke_slash(tree, "music now-playing", music_member, guild)
    [msg] = capture.messages
    assert "no songs playing" in msg.embed["description"].lower()


async def test_music_now_playing_active(tree, guild, music_member):
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


async def test_music_skip_no_current(tree, guild, music_member):
    capture = await invoke_slash(tree, "music skip", music_member, guild)
    [msg] = capture.messages
    assert "no songs playing" in msg.content.lower()


async def test_music_skip_current(tree, guild, music_member, fake_vc):
    musicPlayer.vc = fake_vc
    musicPlayer.sq.curr_song = make_song_item("Current Song")
    capture = await invoke_slash(tree, "music skip", music_member, guild)
    [msg] = capture.messages
    assert "skipped" in msg.content.lower()
    assert "Current Song" in msg.content
    fake_vc.stop.assert_called_once()


async def test_music_skip_queued(tree, guild, music_member):
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


async def test_music_skip_out_of_range(tree, guild, music_member):
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


async def test_music_clear_empty(tree, guild, music_member):
    capture = await invoke_slash(tree, "music clear", music_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_music_clear_with_songs(tree, guild, music_member):
    musicPlayer.sq.queue = deque([make_song_item("X"), make_song_item("Y")])
    capture = await invoke_slash(tree, "music clear", music_member, guild)
    [msg] = capture.messages
    assert "cleared" in msg.content.lower()
    assert list(musicPlayer.sq.queue) == []


# --- /music disconnect ---


async def test_music_disconnect_not_connected(tree, guild, music_member):
    capture = await invoke_slash(tree, "music disconnect", music_member, guild)
    [msg] = capture.messages
    assert "already disconnected" in msg.content.lower()


async def test_music_disconnect_connected(tree, guild, music_member, fake_vc):
    musicPlayer.vc = fake_vc
    capture = await invoke_slash(tree, "music disconnect", music_member, guild)
    [msg] = capture.messages
    assert "disconnected" in msg.content.lower()
    fake_vc.disconnect.assert_awaited_once()


# --- /music shuffle ---


async def test_music_shuffle_empty(tree, guild, music_member):
    capture = await invoke_slash(tree, "music shuffle", music_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_music_shuffle_with_songs(tree, guild, music_member, monkeypatch):
    queue = deque([make_song_item("A"), make_song_item("B")])
    musicPlayer.sq.queue = queue
    shuffle_mock = MagicMock()
    monkeypatch.setattr(musicPlayer.random, "shuffle", shuffle_mock)
    capture = await invoke_slash(tree, "music shuffle", music_member, guild)
    [msg] = capture.messages
    assert "shuffled" in msg.content.lower()
    shuffle_mock.assert_called_once_with(queue)


# --- /music move ---


async def test_music_move_empty(tree, guild, music_member):
    capture = await invoke_slash(
        tree,
        "music move",
        music_member,
        guild,
        options={"move_from": 1, "move_to": 2},
    )
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_music_move_success(tree, guild, music_member):
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


async def test_music_move_out_of_range(tree, guild, music_member):
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


async def test_music_loop_disabled_to_queue(tree, guild, music_member):
    capture = await invoke_slash(tree, "music loop", music_member, guild)
    [msg] = capture.messages
    assert "looped queue" in msg.content.lower()
    assert musicPlayer.loop_status == 1


async def test_music_loop_queue_to_song(tree, guild, music_member):
    musicPlayer.loop_status = 1
    capture = await invoke_slash(tree, "music loop", music_member, guild)
    [msg] = capture.messages
    assert "looped song" in msg.content.lower()
    assert musicPlayer.loop_status == 2


async def test_music_loop_song_to_disabled(tree, guild, music_member):
    musicPlayer.loop_status = 2
    capture = await invoke_slash(tree, "music loop", music_member, guild)
    [msg] = capture.messages
    assert "disabled loop" in msg.content.lower()
    assert musicPlayer.loop_status == 0


# --- on_voice_state_update → reset music state on bot disconnect ---


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
