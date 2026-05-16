"""Integration tests for emote.

- Slash commands dispatch through `tree._call`.
- Gateway events (`on_message`, `on_raw_reaction_add`) dispatch through
  the real `register_event_handlers`-attached handlers via dpytest.

All assertions are on observable behavior — response substrings + DB
state via `emoteLeaderboard.get_emote`.
"""

import asyncio
from unittest.mock import MagicMock

import discord.ext.test as dpytest
import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from components import emoteLeaderboard
from tests._capture import CapturedMessages, make_capturing_channel
from tests._dispatch import invoke_slash, run_periodic_once


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


# --- Gateway events: on_message → check_emoji ---


def _emoji_mock(name: str, emoji_id: int) -> MagicMock:
    e = MagicMock()
    e.name = name
    e.id = emoji_id
    e.animated = False
    return e


@pytest.fixture
async def emote_event_bot(seeded_emote_db, dpytest_client, monkeypatch):
    """Adds the test emojis to `ut.guildObject.emojis` so
    `check_emoji` / `check_reaction` can match the seeded shelve entries
    when the test sends `<:kekw:101>`. dpytest_client (in conftest) does
    the client/dispatcher wiring."""
    monkeypatch.setattr(
        ut.guildObject,
        "emojis",
        [_emoji_mock("kekw", 101), _emoji_mock("pog", 102)],
    )
    return dpytest_client


async def test_on_message_increments_used_emote_score(emote_event_bot):
    before = emoteLeaderboard.get_emote("kekw").score
    await dpytest.message("<:kekw:101>")
    await asyncio.sleep(0)  # let on_message listeners drain
    after = emoteLeaderboard.get_emote("kekw").score
    assert after > before


async def test_on_message_ignores_unknown_emote(emote_event_bot):
    # An emote not in ut.guildObject.emojis is not tracked.
    before = emoteLeaderboard.get_emote("sadge").score
    await dpytest.message("<:sadge:103>")
    await asyncio.sleep(0)
    after = emoteLeaderboard.get_emote("sadge").score
    assert after == before


async def test_on_raw_reaction_add_increments_score(emote_event_bot, monkeypatch):
    """Reactions also feed the leaderboard via check_reaction."""
    # check_reaction calls ut.get_channel(payload.channel_id); stub it so
    # any error path lands somewhere capturable rather than crashing.
    monkeypatch.setattr(ut, "get_channel", lambda _: MagicMock(send=MagicMock()))

    payload = MagicMock()
    payload.channel_id = 999
    payload.emoji.is_custom_emoji.return_value = True
    payload.emoji.animated = False
    payload.emoji.name = "pog"
    payload.emoji.id = 102

    before = emoteLeaderboard.get_emote("pog").score
    emote_event_bot.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)
    after = emoteLeaderboard.get_emote("pog").score
    assert after > before


# --- Periodic task: weekly emote announcement ---


async def test_weekly_announcement_reports_used_emotes(seeded_emote_db, patched_periodic_start, monkeypatch):
    # Drive some w_scores up via the production API.
    emoteLeaderboard.update_counts("<:kekw:101>", 5)
    emoteLeaderboard.update_counts("<:pog:102>", 3)

    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    emoteLeaderboard.init()
    await run_periodic_once(emoteLeaderboard._ANNOUNCEMENT_TASK)

    [msg] = capture.messages
    assert "Weekly emote update" in msg.content
    assert "kekw" in msg.content
    assert "pog" in msg.content

    # Weekly counters reset after announcement.
    assert emoteLeaderboard.get_emote("kekw").w_score == 0
    assert emoteLeaderboard.get_emote("pog").w_score == 0


async def test_weekly_announcement_silent_message_when_no_activity(
    seeded_emote_db, patched_periodic_start, monkeypatch
):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    emoteLeaderboard.init()
    await run_periodic_once(emoteLeaderboard._ANNOUNCEMENT_TASK)

    [msg] = capture.messages
    assert "No emotes were used this week" in msg.content
