"""Tests for meme
Commands: /meme leaderboard
Events: on_message
        on_raw_reaction_add

Verifies leaderboard paging, meme detection from image attachments, and reaction-driven scoring.
"""

import asyncio
import shelve
from unittest.mock import AsyncMock, MagicMock

import discord.ext.test as dpytest
import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from tests._dispatch import invoke_slash
from tests._stubs import patch_channel


@pytest.fixture
def meme_event_env(seeded_meme_db, dpytest_client, guild, monkeypatch):
    # check_meme matches message.channel.id against ut.mainChannel.id;
    # use dpytest's channel as the "main" channel so attachments posted
    # via dpytest.message land where check_meme expects.
    monkeypatch.setattr(ut, "mainChannel", dpytest.get_config().channels[0])
    meme_capture = patch_channel(monkeypatch, ut.env["MEME_CHANNEL"])
    return dpytest_client, meme_capture


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


async def test_on_message_with_image_attachment_counts_as_meme(meme_event_env):
    _, meme_capture = meme_event_env

    await dpytest.message("look at this", attachments=["http://example.com/meme.png"])
    await asyncio.sleep(0)

    author_id = str(dpytest.get_config().members[0].id)

    # Repost lands on memeChannel with the author mention + original image url.
    [msg] = meme_capture.messages
    assert msg.embed["description"] == f"<@{author_id}>"
    assert msg.embed["image"]["url"] == "http://example.com/meme.png"

    # Author had no prior entry; check_meme creates [memer_score=0, daily_meme_count=1].
    with shelve.open("./database/meme_leaderboard.db") as db:
        entry = db.get(author_id)
    assert entry == [0, 1]


async def test_on_message_without_attachment_ignored(meme_event_env):
    _, meme_capture = meme_event_env

    await dpytest.message("just chatting")
    await asyncio.sleep(0)

    assert len(meme_capture.messages) == 0


# --- on_raw_reaction_add → add_meme_reactions ---


async def test_on_raw_reaction_add_good_meme_increments_score(meme_event_env):
    """A 'good meme' reaction ('two') on a tracked meme bumps that meme's
    score AND the reactor's leaderboard. Uses the meme seeded by `seed_meme_review`
    (id=999001, author=alice, score=10).
    """
    client, meme_capture = meme_event_env

    meme_message_id = 999001
    meme_author_id = 101  # alice — matches the seeded entry

    # add_meme_reactions fetches the meme message and inspects it.
    meme_message = MagicMock()
    meme_message.id = meme_message_id
    meme_message.embeds = [MagicMock()]
    meme_message.embeds[0].image.url = "https://example.invalid/meme1.png"
    meme_message.embeds[0].description = f"<@{meme_author_id}>"
    meme_message.reactions = []
    meme_message.remove_reaction = AsyncMock()

    # Reuse the fixture's MEME_CHANNEL channel; just add fetch_message.
    meme_capture.channel.fetch_message = AsyncMock(return_value=meme_message)

    # bob (id=102) is in DEFAULT_MEMBERS via `guild` fixture → guild.get_member(102) returns him.
    payload = MagicMock()
    payload.user_id = 102
    payload.channel_id = meme_capture.channel.id
    payload.message_id = meme_message_id
    payload.emoji = MagicMock()
    payload.emoji.name = "two"  # goodMeme, worth 2

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        score = db[str(meme_message_id)][0]
    assert score == 12  # 10 (seeded) + 2 (goodMeme reaction)

    with shelve.open("./database/meme_leaderboard.db") as db:
        bob_entry = db.get("102")
    assert bob_entry is not None
    assert bob_entry[0] == 31  # 30 (seeded) + 1 for reacting
