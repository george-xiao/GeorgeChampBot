"""Tests for emote
Commands: /emote count
          /emote leaderboard
          /admin emote transfer
          /admin emote delete
          /admin emote add-score
Events: on_message
        on_raw_reaction_add
        on_guild_emojis_update
Startup: init_emote_leaderboard

Verifies score counting, leaderboard paging, admin mutations, emoji add/remove/rename tracking, and offline reconciliation.
"""

import asyncio
import shelve
from unittest.mock import MagicMock

import discord.ext.test as dpytest
import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from components import emoteLeaderboard
from components.emoteLeaderboard import Emoji
from tests._dispatch import invoke_slash
from tests._factories import make_emoji
from tests._stubs import patch_bot_channel, patch_main_channel


@pytest.fixture
async def emote_event_env(seeded_emote_db, dpytest_client, monkeypatch):
    """Adds the test emojis to `ut.guildObject.emojis` so `check_emoji` / `check_reaction`
    can match the seeded shelve entries when the test sends `<:kekw:101>`
    dpytest_client (in conftest) does the client/dispatcher wiring
    """
    monkeypatch.setattr(
        ut.guildObject,
        "emojis",
        [make_emoji("kekw", 101), make_emoji("pog", 102)],
    )
    return dpytest_client


# --- /emote count ---


async def test_emote_count_existing(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote count",
        regular_member,
        guild,
        options={"emote": "kekw"},
    )
    [msg] = capture.messages
    assert "kekw" in msg.content
    assert "500" in msg.content


async def test_emote_count_missing(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote count",
        regular_member,
        guild,
        options={"emote": "nonexistent"},
    )
    [msg] = capture.messages
    assert "couldn't find" in msg.content.lower()


# --- /emote leaderboard ---


async def test_emote_leaderboard_page_1(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote leaderboard",
        regular_member,
        guild,
        options={"page": 1},
    )
    [msg] = capture.messages
    # Page 1 shows top 10 active emotes
    assert "kekw" in msg.content
    assert "500" in msg.content
    assert "Page 1/2" in msg.content


async def test_emote_leaderboard_page_2(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote leaderboard",
        regular_member,
        guild,
        options={"page": 2},
    )
    [msg] = capture.messages
    assert "clap" in msg.content
    assert "Page 2/2" in msg.content


async def test_emote_leaderboard_last(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote leaderboard",
        regular_member,
        guild,
        options={"show_last": True},
    )
    [msg] = capture.messages
    assert "Page 2/2" in msg.content


async def test_emote_leaderboard_deleted(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote leaderboard",
        regular_member,
        guild,
        options={"show_deleted": True},
    )
    [msg] = capture.messages
    assert "oldmeme" in msg.content
    assert "retired" in msg.content


async def test_emote_leaderboard_empty_page(seeded_emote_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "emote leaderboard",
        regular_member,
        guild,
        options={"page": 99},
    )
    [msg] = capture.messages
    assert "another page" in msg.content.lower() or "doesn't look" in msg.content.lower()


# --- /admin emote transfer ---


async def test_emote_transfer_success(seeded_emote_db, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin emote transfer",
        admin_member,
        guild,
        options={"emote_from": "oldmeme", "emote_to": "kekw"},
    )
    [msg] = capture.messages
    assert "successful" in msg.content.lower()
    assert emoteLeaderboard.get_emote("kekw").score == 580
    assert emoteLeaderboard.get_emote("oldmeme") is None


async def test_emote_transfer_failed(seeded_emote_db, tree, guild, admin_member):
    # kekw is active, not deleted → transferring FROM it must fail
    capture = await invoke_slash(
        tree,
        "admin emote transfer",
        admin_member,
        guild,
        options={"emote_from": "kekw", "emote_to": "pog"},
    )
    [msg] = capture.messages
    assert "couldn't" in msg.content.lower()
    assert emoteLeaderboard.get_emote("kekw").score == 500
    assert emoteLeaderboard.get_emote("pog").score == 350


# --- /admin emote delete ---


async def test_emote_delete_success(seeded_emote_db, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin emote delete",
        admin_member,
        guild,
        options={"emote": "oldmeme"},
    )
    [msg] = capture.messages
    assert "deleted" in msg.content.lower()
    assert emoteLeaderboard.get_emote("oldmeme") is None


async def test_emote_delete_active(seeded_emote_db, tree, guild, admin_member):
    # kekw is active (not soft-deleted) → hard delete should refuse
    capture = await invoke_slash(
        tree,
        "admin emote delete",
        admin_member,
        guild,
        options={"emote": "kekw"},
    )
    [msg] = capture.messages
    assert "couldn't find" in msg.content.lower()
    assert emoteLeaderboard.get_emote("kekw") is not None


# --- /admin emote add-score ---


async def test_emote_add_score_existing(seeded_emote_db, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin emote add-score",
        admin_member,
        guild,
        options={"emote": "kekw", "score": 100},
    )
    [msg] = capture.messages
    assert "600" in msg.content
    assert emoteLeaderboard.get_emote("kekw").score == 600


async def test_emote_add_score_missing(seeded_emote_db, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin emote add-score",
        admin_member,
        guild,
        options={"emote": "ghostemote", "score": 50},
    )
    [msg] = capture.messages
    assert "couldn't find" in msg.content.lower()
    assert emoteLeaderboard.get_emote("ghostemote") is None


# --- on_message → check_emoji ---


async def test_on_message_increments_used_emote_score(emote_event_env):
    before = emoteLeaderboard.get_emote("kekw").score
    await dpytest.message("<:kekw:101>")
    await asyncio.sleep(0)  # let on_message listeners drain
    after = emoteLeaderboard.get_emote("kekw").score
    # One emoji in the message → score_algorithm(1) = round(0.61) = 1 increment.
    assert after == before + 1


async def test_on_message_ignores_unknown_emote(emote_event_env):
    # An emote not in ut.guildObject.emojis is not tracked.
    before = emoteLeaderboard.get_emote("sadge").score
    await dpytest.message("<:sadge:103>")
    await asyncio.sleep(0)
    after = emoteLeaderboard.get_emote("sadge").score
    assert after == before


async def test_on_raw_reaction_add_increments_score(emote_event_env):
    """Reactions also feed the leaderboard via check_reaction."""
    payload = MagicMock()
    payload.emoji.is_custom_emoji.return_value = True
    payload.emoji.animated = False
    payload.emoji.name = "pog"
    payload.emoji.id = 102

    before = emoteLeaderboard.get_emote("pog").score
    emote_event_env.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)
    after = emoteLeaderboard.get_emote("pog").score
    # check_reaction calls update_counts with default increment=1.
    assert after == before + 1


# --- on_guild_emojis_update → rename_emote ---


async def test_on_guild_emojis_update_adds_new_emoji(seeded_emote_db, ut_client_ready, monkeypatch):
    capture = patch_bot_channel(monkeypatch)

    new = make_emoji("wow", 999)
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [], [new])
    await asyncio.sleep(0)

    assert emoteLeaderboard.get_emote("wow") is not None
    assert any("wow" in m.content and "added" in m.content for m in capture.messages)


async def test_on_guild_emojis_update_marks_removed_emoji_deleted(seeded_emote_db, ut_client_ready, monkeypatch):
    # kekw is in the seed with score=500 → soft-delete (entry stays, deleted flag flips)
    capture = patch_bot_channel(monkeypatch)

    gone = make_emoji("kekw", 101)
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [gone], [])
    await asyncio.sleep(0)

    emote = emoteLeaderboard.get_emote("kekw")
    assert emote is not None
    assert emote.deleted is True
    assert any("kekw" in m.content and "deleted" in m.content for m in capture.messages)


async def test_on_guild_emojis_update_rename_is_remove_then_add(seeded_emote_db, ut_client_ready, monkeypatch):
    # Same id, different name → before/after dnames differ → remove old + add new
    capture = patch_bot_channel(monkeypatch)

    old = make_emoji("kekw", 101)
    renamed = make_emoji("kekw_renamed", 101)
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [old], [renamed])
    await asyncio.sleep(0)

    assert emoteLeaderboard.get_emote("kekw").deleted is True
    assert emoteLeaderboard.get_emote("kekw_renamed") is not None
    # Both the deleted and added announcements should have landed.
    assert any("kekw" in m.content and "deleted" in m.content for m in capture.messages)
    assert any("kekw_renamed" in m.content and "added" in m.content for m in capture.messages)


async def test_on_guild_emojis_update_hard_deletes_zero_score_emoji(seeded_emote_db, ut_client_ready, monkeypatch):
    # Seed a zero-score entry; remove_emote deletes it outright (vs. soft-delete for nonzero scores).
    with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s:
        s["fresh"] = Emoji("fresh", "<:fresh:777>", score=0)

    capture = patch_bot_channel(monkeypatch)

    gone = make_emoji("fresh", 777)
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [gone], [])
    await asyncio.sleep(0)

    assert emoteLeaderboard.get_emote("fresh") is None
    assert any("fresh" in m.content and "deleted" in m.content for m in capture.messages)


async def test_on_guild_emojis_update_re_add_clears_deleted_flag(seeded_emote_db, ut_client_ready, monkeypatch):
    # oldmeme is seeded with deleted=True, score=80; re-adding flips deleted back to False.
    assert emoteLeaderboard.get_emote("oldmeme").deleted is True

    capture = patch_bot_channel(monkeypatch)

    revived = make_emoji("oldmeme", 201)
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [], [revived])
    await asyncio.sleep(0)

    revived_emote = emoteLeaderboard.get_emote("oldmeme")
    assert revived_emote is not None
    assert revived_emote.deleted is False
    assert revived_emote.score == 80  # score preserved across the revive
    assert any("oldmeme" in m.content and "added" in m.content for m in capture.messages)


async def test_on_guild_emojis_update_no_op_emits_no_changes(seeded_emote_db, ut_client_ready, monkeypatch):
    capture = patch_bot_channel(monkeypatch)

    kekw = make_emoji("kekw", 101)
    score_before = emoteLeaderboard.get_emote("kekw").score
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [kekw], [kekw])
    await asyncio.sleep(0)

    assert capture.messages == []
    assert emoteLeaderboard.get_emote("kekw").score == score_before
    assert emoteLeaderboard.get_emote("kekw").deleted is False


async def test_on_guild_emojis_update_batch_add_and_remove(seeded_emote_db, ut_client_ready, monkeypatch):
    # Two adds + two removes in one event; every entry should be processed.
    capture = patch_bot_channel(monkeypatch)

    before = [make_emoji("kekw", 101), make_emoji("pog", 102)]
    after = [make_emoji("alpha", 555), make_emoji("beta", 666)]
    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, before, after)
    await asyncio.sleep(0)

    assert emoteLeaderboard.get_emote("kekw").deleted is True
    assert emoteLeaderboard.get_emote("pog").deleted is True
    assert emoteLeaderboard.get_emote("alpha") is not None
    assert emoteLeaderboard.get_emote("beta") is not None
    # All four announcements landed.
    for name, verb in [("kekw", "deleted"), ("pog", "deleted"), ("alpha", "added"), ("beta", "added")]:
        assert any(
            name in m.content and verb in m.content for m in capture.messages
        ), f"missing {verb} message for {name}"


async def test_on_guild_emojis_update_error_path_sends_error_message(seeded_emote_db, ut_client_ready, monkeypatch):
    # Pass [None] as input → rename_emote naturally fails on None.name access.
    # Its own try/except catches and sends "Error Renaming Emotes" to mainChannel.
    capture = patch_main_channel(monkeypatch)

    ut_client_ready.dispatch("guild_emojis_update", ut.guildObject, [None], [None])
    await asyncio.sleep(0)

    [msg] = capture.messages
    assert "Error Renaming Emotes" in msg.content


# --- init_emote_leaderboard (offline reconciliation) ---


async def test_init_emote_leaderboard_adds_emote_present_in_guild(db_dir, guild, monkeypatch):
    """An emoji present in the guild but missing from the DB is added (e.g. added while offline)."""
    patch_bot_channel(monkeypatch)
    monkeypatch.setattr(ut.guildObject, "emojis", [make_emoji("wow", 999)])

    await emoteLeaderboard.init_emote_leaderboard()

    added = emoteLeaderboard.get_emote("wow")
    assert added is not None
    assert added.deleted is False


async def test_init_emote_leaderboard_removes_emote_absent_from_guild(db_dir, guild, monkeypatch):
    """A tracked emote no longer present in the guild is soft-deleted (e.g. removed while offline)."""
    patch_bot_channel(monkeypatch)
    with shelve.open("./database/all_time_georgechamp_shelf.db") as s:
        s["kekw"] = Emoji("kekw", "<:kekw:101>", score=500)
    monkeypatch.setattr(ut.guildObject, "emojis", [])  # kekw is gone from the guild

    await emoteLeaderboard.init_emote_leaderboard()

    assert emoteLeaderboard.get_emote("kekw").deleted is True


async def test_init_emote_leaderboard_sets_starting_date_when_missing(db_dir, guild, monkeypatch):
    """First run seeds the leaderboard's start date."""
    patch_bot_channel(monkeypatch)
    monkeypatch.setattr(ut.guildObject, "emojis", [])

    await emoteLeaderboard.init_emote_leaderboard()

    with shelve.open("./database/starting_date_shelf.db") as s:
        assert "date" in s
