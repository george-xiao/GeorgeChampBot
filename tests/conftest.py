"""Pytest fixtures.

NOTE: `_env_setup` is imported FIRST. It sets placeholder env vars before
common.utils is loaded by any subsequent import. Without this, common.utils
crashes at import time on ANNOUNCEMENT_DAY/HOUR/MIN int casts.
"""

from tests import _env_setup  # noqa: F401  (must come before any common.* import)

from pathlib import Path

import pytest

from tests._factories import DEFAULT_MEMBERS, make_guild


@pytest.fixture(scope="session")
def tree():
    """The production CommandTree, built once per test session via
    `commands.load_commands`. Tests dispatch on this exact tree —
    matching how `GeorgeChampBot.on_ready` wires production.
    """
    import discord
    from discord import app_commands
    from commands import load_commands

    client = discord.Client(intents=discord.Intents.default())
    tree = app_commands.CommandTree(client)
    load_commands(tree)
    return tree


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
def guild(members, monkeypatch):
    """Test guild built from DEFAULT_MEMBERS. Also patches ut.guildObject
    so production code paths that read it (ut.get_member, ut.fetch_member,
    etc.) see the rich members list instead of the empty bootstrap guild
    installed by tests/_env_setup.py."""
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


@pytest.fixture
def patched_periodic_start(monkeypatch):
    """Disable PeriodicTask.start so a component's init() wires the task
    without launching the background scheduler. Drive via run_periodic_once
    instead."""
    from common.periodicTask import PeriodicTask

    monkeypatch.setattr(PeriodicTask, "start", lambda self, *a, **k: None)


@pytest.fixture
async def ut_client_ready():
    """Bind ut.client to the current test's event loop. Production event
    handlers register on ut.client at GeorgeChampBot import time
    (module-level @ut.client.event decorators); this fixture ensures
    `_async_setup_hook` has been called against this test's loop so
    `ut.client.dispatch(...)` works."""
    import common.utils as ut
    import GeorgeChampBot  # noqa: F401 — triggers @ut.client.event registration

    await ut.client._async_setup_hook()
    return ut.client


@pytest.fixture
async def dpytest_client(ut_client_ready):
    """ut.client wired into dpytest's runner. Clean queue between tests."""
    import discord.ext.test as dpytest

    dpytest.configure(ut_client_ready)
    try:
        yield ut_client_ready
    finally:
        await dpytest.empty_queue()
