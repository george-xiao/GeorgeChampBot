"""Pytest fixtures.

NOTE: `_env_setup` is imported FIRST. It sets placeholder env vars before
common.utils is loaded by any subsequent import. Without this, common.utils
crashes at import time on ANNOUNCEMENT_DAY/HOUR/MIN int casts.
"""

from tests import _env_setup  # noqa: F401  (must come before any common.* import)

import os
from pathlib import Path

import pytest

from tests._fixtures import DEFAULT_MEMBERS, make_guild


@pytest.fixture
def db_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Move CWD to a tmp directory with a fresh `database/` subfolder.

    All components open shelve DBs with relative paths like
    './database/meme_leaderboard.db'. Chdir-ing here makes those land in
    the tmp dir, so tests don't touch the real database/.
    """
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "database"
    db.mkdir()
    return db


@pytest.fixture
def members():
    return DEFAULT_MEMBERS


@pytest.fixture
def guild(members):
    return make_guild(members)


@pytest.fixture
def admin_member(members):
    return members[-1]  # eve has admin


@pytest.fixture
def regular_member(members):
    return members[0]  # alice


@pytest.fixture
def snapshots_dir() -> Path:
    return Path(__file__).parent / "snapshots"


@pytest.fixture
def seeded_meme_db(db_dir):
    from tests._fixtures import seed_meme_leaderboard, seed_meme_review
    seed_meme_leaderboard(db_dir)
    seed_meme_review(db_dir)
    return db_dir


@pytest.fixture
def seeded_dota_db(db_dir):
    from tests._fixtures import seed_dota_player_list
    seed_dota_player_list(db_dir)
    return db_dir


@pytest.fixture
def seeded_twitch_db(db_dir):
    from tests._fixtures import seed_twitch_streamer_list
    seed_twitch_streamer_list(db_dir)
    return db_dir


@pytest.fixture
def seeded_emote_db(db_dir):
    from tests._fixtures import seed_emote_leaderboard
    seed_emote_leaderboard(db_dir)
    return db_dir


@pytest.fixture
def ut_globals(monkeypatch, guild):
    """Point common.utils.guildObject at the test guild so ut.get_member /
    ut.get_member_str / ut.get_role work for code under test.
    """
    import common.utils as ut
    monkeypatch.setattr(ut, "guildObject", guild)
    return guild


@pytest.fixture
def seeded_movie_db(db_dir):
    from tests._fixtures import seed_movie_suggestions
    seed_movie_suggestions(db_dir)
    return db_dir


@pytest.fixture
def snap_send(guild, regular_member, snapshots_dir):
    """Bundles capture + send + snapshot assertion. Pass any of:
      str          → sent via interaction.response.send_message(content)
      discord.Embed → sent via interaction.response.send_message(embed=...)
      list[str]    → each element sent via interaction.followup.send(...)
    """
    import discord
    from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot

    async def _send(result, snapshot_name, *, user=None):
        capture = CapturedMessages()
        interaction = make_capturing_interaction(user or regular_member, guild, capture)
        if isinstance(result, list):
            for msg in result:
                await interaction.followup.send(msg)
        elif isinstance(result, discord.Embed):
            await interaction.response.send_message(embed=result)
        else:
            await interaction.response.send_message(result)
        assert_snapshot(capture.to_normalized_list(), snapshot_name, snapshots_dir)

    return _send
