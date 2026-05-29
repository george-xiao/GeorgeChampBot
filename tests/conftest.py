"""Shared fixtures for all tests.

NOTE: `_env_setup` must be imported first — it sets placeholder env vars
before common.utils loads (which crashes without them).
"""

from tests import _env_setup  # noqa: F401  (must come before any common.* import)

from pathlib import Path

import pytest

from tests._factories import DEFAULT_MEMBERS, make_guild


# --- Core ---


@pytest.fixture(scope="session")
def tree():
    """Production command tree with all slash commands loaded. Session-scoped."""
    import discord
    from discord import app_commands
    from commands import load_commands

    client = discord.Client(intents=discord.Intents.default())
    tree = app_commands.CommandTree(client)
    load_commands(tree)
    return tree


@pytest.fixture
def db_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temp directory with a `database/` subfolder. CWD is moved here so
    shelve operations don't touch the real database."""
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "database"
    db.mkdir()
    return db


@pytest.fixture
def tasks_noop(monkeypatch):
    """Disable all background task scheduling. Opt-in for tests/immediate/ tests that
    would otherwise kick off periodic/async tasks during their immediate code path."""
    from common.asyncTask import AsyncTask
    from common.periodicTask import PeriodicTask

    monkeypatch.setattr(PeriodicTask, "start", lambda self, *a, **k: None)
    monkeypatch.setattr(AsyncTask, "start", lambda self, *a, **k: None)


# --- Discord objects ---


@pytest.fixture
def members():
    return DEFAULT_MEMBERS


@pytest.fixture
def guild(members, monkeypatch):
    """Fake guild with 5 members. Patches ut.guildObject globally."""
    g = make_guild(members)
    import common.utils as ut

    monkeypatch.setattr(ut, "guildObject", g)
    return g


@pytest.fixture
def admin_member(members):
    return members[-1]  # eve has admin


@pytest.fixture
def regular_member(members):
    return members[0]  # alice


# --- Seeded databases ---


@pytest.fixture
def seeded_meme_db(db_dir):
    from tests._factories import seed_meme_leaderboard, seed_meme_review

    seed_meme_leaderboard(db_dir)
    seed_meme_review(db_dir)
    return db_dir


@pytest.fixture
def seeded_dota_db(db_dir):
    from tests._factories import seed_dota_player_list

    seed_dota_player_list(db_dir)
    return db_dir


@pytest.fixture
def seeded_twitch_db(db_dir):
    from tests._factories import seed_twitch_streamer_list

    seed_twitch_streamer_list(db_dir)
    return db_dir


@pytest.fixture
def seeded_emote_db(db_dir):
    from tests._factories import seed_emote_leaderboard

    seed_emote_leaderboard(db_dir)
    return db_dir


@pytest.fixture
def seeded_movie_db(db_dir):
    from tests._factories import seed_movie_suggestions

    seed_movie_suggestions(db_dir)
    return db_dir


# --- Event dispatch (dpytest) ---


@pytest.fixture
async def ut_client_ready():
    """ut.client ready for dispatch. Use for gateway event tests via client.dispatch(...)."""
    import common.utils as ut
    import GeorgeChampBot  # noqa: F401 — triggers @ut.client.event registration

    await ut.client._async_setup_hook()
    return ut.client


@pytest.fixture
async def dpytest_client(ut_client_ready):
    """ut.client wired into dpytest. Use for dpytest.message(...) tests."""
    import discord.ext.test as dpytest

    dpytest.configure(ut_client_ready)
    try:
        yield ut_client_ready
    finally:
        await dpytest.empty_queue()


# --- Music ---


@pytest.fixture
def voice_channel():
    from unittest.mock import MagicMock

    channel = MagicMock()
    channel.id = 5555
    channel.members = []
    return channel


@pytest.fixture
def fake_vc(voice_channel):
    """discord.VoiceClient mock with the full surface used by music tests.
    voice_channel.connect is wired so production's `await user.voice.channel.connect()` returns this fake."""
    from unittest.mock import AsyncMock, MagicMock

    import discord

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
    """`regular_member` (alice) with .voice.channel set so `require_voice` passes."""
    from unittest.mock import MagicMock

    regular_member.voice = MagicMock()
    regular_member.voice.channel = voice_channel
    return regular_member
