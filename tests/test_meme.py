"""Tests for meme.

- Slash commands dispatch through `tree._call`.
- Gateway events (`on_message` → `check_meme`, `on_raw_reaction_add` →
  `add_meme_reactions`) dispatch through dpytest / `client.dispatch`.
- Periodic tasks (weekly best-meme + daily counter reset) dispatch via
  `run_periodic_once` on the actual tasks `memeReview.init()` wires up.
"""

import asyncio
import shelve
from unittest.mock import AsyncMock, MagicMock

import discord
import discord.ext.test as dpytest
import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from components import memeReview
from tests._capture import CapturedMessages, SentMessage, make_capturing_channel
from tests._dispatch import invoke_slash, run_periodic_once


# --- /meme leaderboard ---


async def test_meme_leaderboard_default_page(seeded_meme_db, tree, guild, regular_member):
    capture = await invoke_slash(tree, "meme leaderboard", regular_member, guild)
    [msg] = capture.messages
    assert "Meme Leaderboard" in msg.content
    assert "Page 1/1" in msg.content
    # Seed: alice 50, bob 30, carol 25, dave 10, eve 5 — all five rendered.
    for name in ("Alice the Great", "bob", "Carol", "dave", "Eve"):
        assert name in msg.content


async def test_meme_leaderboard_empty_page(seeded_meme_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "meme leaderboard",
        regular_member,
        guild,
        options={"page": 2},
    )
    [msg] = capture.messages
    assert "another page" in msg.content.lower()


# --- on_message → check_meme ---


@pytest.fixture
def meme_event_bot(seeded_meme_db, dpytest_client, monkeypatch):
    # check_meme matches message.channel.id against ut.mainChannel.id;
    # use dpytest's channel as the "main" channel so attachments posted
    # via dpytest.message land where check_meme expects.
    dpytest_channel = dpytest.get_config().channels[0]
    monkeypatch.setattr(ut, "mainChannel", dpytest_channel)

    # check_meme reposts to ut.get_channel(MEME_CHANNEL) — capture it
    # with a channel whose .send returns a message-like mock so
    # check_meme can store the message id and add (no-op) reactions.
    meme_capture = CapturedMessages()

    async def _send(content="", embed=None, delete_after=None, **kwargs):
        meme_capture.messages.append(
            SentMessage(
                content=content or "",
                embed=embed.to_dict() if isinstance(embed, discord.Embed) else None,
                delete_after=delete_after,
            )
        )
        msg = MagicMock()
        msg.id = len(meme_capture.messages)
        msg.add_reaction = AsyncMock()
        return msg

    meme_channel = MagicMock()
    meme_channel.send = _send
    meme_channel.id = 7777
    monkeypatch.setattr(ut, "get_channel", lambda _: meme_channel)

    return dpytest_client, meme_capture, meme_channel


async def test_on_message_with_image_attachment_counts_as_meme(meme_event_bot):
    _, meme_capture, _ = meme_event_bot

    await dpytest.message("look at this", attachments=["http://example.com/meme.png"])
    await asyncio.sleep(0)

    # Repost lands on memeChannel.
    assert len(meme_capture.messages) == 1
    assert meme_capture.messages[0].embed is not None

    # Author's daily count incremented in meme_leaderboard.
    author_id = str(dpytest.get_config().members[0].id)
    with shelve.open("./database/meme_leaderboard.db") as db:
        entry = db.get(author_id)
    assert entry is not None
    assert entry[1] >= 1


async def test_on_message_without_attachment_ignored(meme_event_bot):
    _, meme_capture, _ = meme_event_bot

    await dpytest.message("just chatting")
    await asyncio.sleep(0)

    assert len(meme_capture.messages) == 0


# --- on_raw_reaction_add → add_meme_reactions ---


async def test_on_raw_reaction_add_good_meme_increments_score(meme_event_bot, monkeypatch):
    """A 'good meme' reaction ('two') on a tracked meme bumps that meme's
    score AND the reactor's leaderboard.
    """
    client, _, _ = meme_event_bot

    meme_message_id = 999001
    meme_author_id = 101  # alice
    with shelve.open("./database/meme_review.db", writeback=True) as db:
        db[str(meme_message_id)] = [0, True, meme_author_id, "http://example.com/x.png"]

    # add_meme_reactions fetches the meme message and inspects it.
    meme_message = MagicMock()
    meme_message.id = meme_message_id
    meme_message.embeds = [MagicMock()]
    meme_message.embeds[0].image.url = "http://example.com/x.png"
    meme_message.embeds[0].description = f"<@{meme_author_id}>"
    meme_message.reactions = []
    meme_message.remove_reaction = AsyncMock()

    meme_channel = MagicMock()
    meme_channel.id = 7777
    meme_channel.fetch_message = AsyncMock(return_value=meme_message)
    meme_channel.send = AsyncMock()
    monkeypatch.setattr(ut, "get_channel", lambda _: meme_channel)

    reactor = MagicMock()
    reactor.id = 102  # bob
    reactor.bot = False
    monkeypatch.setattr(ut.guildObject, "get_member", lambda _id: reactor)

    admin_role = MagicMock()
    admin_role.members = []
    monkeypatch.setattr(ut, "get_role", lambda _: admin_role)

    payload = MagicMock()
    payload.user_id = 102
    payload.channel_id = 7777
    payload.message_id = meme_message_id
    payload.emoji = MagicMock()
    payload.emoji.name = "two"  # goodMeme, worth 2

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        score = db[str(meme_message_id)][0]
    assert score == 2

    with shelve.open("./database/meme_leaderboard.db") as db:
        bob_entry = db.get("102")
    assert bob_entry is not None
    assert bob_entry[0] == 31  # 30 (seeded) + 1 for reacting


# --- Periodic: weekly best-meme announcement + daily reset ---


async def test_weekly_best_meme_announces_to_main_channel(seeded_meme_db, patched_periodic_start, monkeypatch):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    memeReview.init()
    await run_periodic_once(memeReview._BEST_ANNOUNCEMENT_TASK)

    [msg] = capture.messages
    assert "Memer of the Week" in msg.content


async def test_weekly_best_meme_handles_no_memes(db_dir, patched_periodic_start, monkeypatch):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "mainChannel", channel)

    memeReview.init()
    await run_periodic_once(memeReview._BEST_ANNOUNCEMENT_TASK)

    [msg] = capture.messages
    assert "No memes" in msg.content


async def test_daily_reset_clears_daily_meme_counts(seeded_meme_db, patched_periodic_start):
    with shelve.open("./database/meme_leaderboard.db", writeback=True) as db:
        db["101"] = [50, 3]
    memeReview.init()
    await run_periodic_once(memeReview._RESET_LIMIT_TASK)

    with shelve.open("./database/meme_leaderboard.db") as db:
        alice_after = db["101"]
    assert alice_after[0] == 50
    assert alice_after[1] == 0
