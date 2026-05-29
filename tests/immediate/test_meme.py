"""Tests for meme
Commands: /meme leaderboard
Events: on_message
        on_raw_reaction_add
        on_raw_reaction_remove

Verifies leaderboard paging, meme detection from image attachments, and reaction-driven scoring (add + remove).
"""

import asyncio
import shelve
from unittest.mock import AsyncMock, MagicMock

import discord.ext.test as dpytest
import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from components import memeReview
from tests._dispatch import invoke_slash
from tests._factories import make_emoji
from tests._stubs import patch_channel


@pytest.fixture
def meme_event_env(seeded_meme_db, dpytest_client, guild, monkeypatch):
    # check_meme matches message.channel.id against ut.mainChannel.id;
    # use dpytest's channel as the "main" channel so attachments posted
    # via dpytest.message land where check_meme expects.
    monkeypatch.setattr(ut, "mainChannel", dpytest.get_config().channels[0])
    meme_capture = patch_channel(monkeypatch, ut.env["MEME_CHANNEL"])
    return dpytest_client, meme_capture


# Builders for reaction-handler tests. add_meme_reactions / remove_meme_reactions
# fetch the meme message, then inspect its embed + reactions.


def _meme_message(message_id, *, author_id=101, image_url="https://example.invalid/meme1.png", reactions=None):
    msg = MagicMock()
    msg.id = message_id
    msg.embeds = [MagicMock()]
    msg.embeds[0].image.url = image_url
    msg.embeds[0].description = f"<@{author_id}>"  # getUser() reads description[2:-1]
    msg.reactions = reactions if reactions is not None else []
    msg.remove_reaction = AsyncMock()
    return msg


def _meme_reaction(emoji_name, *, count=1, users=()):
    r = MagicMock()
    r.emoji = emoji_name  # str → handlers use it directly (no .name lookup)
    r.count = count

    async def _users():
        for u in users:
            yield u

    r.users = _users
    return r


def _reaction_payload(*, user_id, message_id, emoji_name, channel_id):
    p = MagicMock()
    p.user_id = user_id
    p.message_id = message_id
    p.channel_id = channel_id
    p.emoji = MagicMock()
    p.emoji.name = emoji_name
    return p


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


async def test_on_message_meme_gets_vote_reactions(meme_event_env, monkeypatch):
    """check_meme seeds the reposted meme with the five vote emojis present in the guild."""
    _, meme_capture = meme_event_env
    monkeypatch.setattr(
        ut.guildObject,
        "emojis",
        [
            make_emoji(memeReview.notMeme, 1),
            make_emoji(memeReview.badMeme, 2),
            make_emoji(memeReview.ehMeme, 3),
            make_emoji(memeReview.goodMeme, 4),
            make_emoji(memeReview.bestMeme, 5),
        ],
    )

    await dpytest.message("look at this", attachments=["http://example.com/meme.png"])
    await asyncio.sleep(0)

    [meme_msg] = meme_capture.sent  # the reposted meme message
    assert meme_msg.add_reaction.await_count == 5  # one reaction per vote emoji


async def test_on_message_meme_rejected_when_daily_limit_hit(meme_event_env):
    """A second meme the same day is rejected (not reposted, daily count untouched)."""
    _, meme_capture = meme_event_env
    author_id = str(dpytest.get_config().members[0].id)
    with shelve.open("./database/meme_leaderboard.db") as db:
        db[author_id] = [0, 1]  # already posted a meme today

    await dpytest.message("again", attachments=["http://example.com/meme2.png"])
    await asyncio.sleep(0)

    assert meme_capture.messages == []  # no repost to memeChannel
    with shelve.open("./database/meme_leaderboard.db") as db:
        assert db[author_id] == [0, 1]  # unchanged — not counted again


async def test_on_message_meme_increments_existing_author(meme_event_env):
    """An author with a prior score (but no meme yet today) keeps the score and gets daily count = 1."""
    _, meme_capture = meme_event_env
    author_id = str(dpytest.get_config().members[0].id)
    with shelve.open("./database/meme_leaderboard.db") as db:
        db[author_id] = [7, 0]

    await dpytest.message("look", attachments=["http://example.com/meme.png"])
    await asyncio.sleep(0)

    with shelve.open("./database/meme_leaderboard.db") as db:
        assert db[author_id] == [7, 1]  # score preserved, daily count incremented
    assert len(meme_capture.messages) == 1  # reposted


async def test_on_message_video_meme_posts_url(meme_event_env):
    """A video attachment is reposted as a raw URL (embeds don't render video) alongside the embed."""
    _, meme_capture = meme_event_env

    await dpytest.message("clip", attachments=["http://example.com/clip.mp4"])
    await asyncio.sleep(0)

    contents = [m.content for m in meme_capture.messages]
    assert "http://example.com/clip.mp4" in contents


# --- on_raw_reaction_add → add_meme_reactions ---


async def test_on_raw_reaction_add_good_meme_increments_score(meme_event_env):
    """A 'good meme' reaction ('two') on a tracked meme bumps that meme's
    score AND the reactor's leaderboard. Uses the meme seeded by `seed_meme_review`
    (id=999001, author=alice, score=10).
    """
    client, meme_capture = meme_event_env

    # Seeded meme 999001 (author=alice/101). bob (102) is in DEFAULT_MEMBERS → guild.get_member(102) returns him.
    meme_message = _meme_message(999001)
    meme_capture.channel.fetch_message = AsyncMock(return_value=meme_message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        score = db["999001"][0]
    assert score == 12  # 10 (seeded) + 2 (goodMeme reaction)

    with shelve.open("./database/meme_leaderboard.db") as db:
        bob_entry = db.get("102")
    assert bob_entry is not None
    assert bob_entry[0] == 31  # 30 (seeded) + 1 for reacting


async def test_add_meme_reactions_tracks_new_meme_and_scores(meme_event_env):
    """Reacting on a meme not yet in meme_review.db creates its entry, then scores it."""
    client, meme_capture = meme_event_env
    message = _meme_message(999002)  # not seeded
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999002, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999002"][0] == 2  # created [0,...] then +getScore(goodMeme)=2
    with shelve.open("./database/meme_leaderboard.db") as db:
        assert db["102"] == [31, 0]  # bob +1 for reacting (was [30, 0])


async def test_add_meme_reactions_admin_marks_not_a_meme(meme_event_env):
    """An admin reacting 'not a meme' flags the meme and decrements the author's daily count."""
    client, meme_capture = meme_event_env
    admin_role = ut.get_role(ut.env["ADMIN_ROLE"])
    admin_role.members = [ut.guildObject.get_member(102)]  # bob is admin via the role's member list

    message = _meme_message(999001, reactions=[_meme_reaction(memeReview.notMeme, count=1)])
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.notMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999001"][1] is False  # flagged "not a meme"
    with shelve.open("./database/meme_leaderboard.db") as db:
        assert db["101"] == [50, -1]  # alice's daily count reduced


async def test_add_meme_reactions_removes_vote_on_flagged_meme(meme_event_env):
    """A new vote on a meme already carrying a 'not a meme' reaction (count > 1) is removed."""
    client, meme_capture = meme_event_env
    message = _meme_message(999001, reactions=[_meme_reaction(memeReview.notMeme, count=2)])
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    message.remove_reaction.assert_awaited_once()


async def test_add_meme_reactions_ignores_non_image_embed(meme_event_env):
    """If the fetched message's embed image isn't an image/video, the meme is left untouched."""
    client, meme_capture = meme_event_env
    message = _meme_message(999001, image_url="https://example.invalid/notes.txt")
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999001"][0] == 10  # unchanged


async def test_add_meme_reactions_replaces_previous_vote(meme_event_env):
    """A reactor switching votes (good → best) has their earlier reaction removed."""
    client, meme_capture = meme_event_env
    reactor = ut.guildObject.get_member(102)
    prior = _meme_reaction(memeReview.goodMeme, count=1, users=[reactor])  # bob's earlier 'good' vote
    message = _meme_message(999001, reactions=[prior])
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.bestMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    message.remove_reaction.assert_awaited_once()  # the prior 'good' vote is removed


async def test_add_meme_reactions_removes_self_reaction_on_own_meme(meme_event_env):
    """The meme's author can't vote on their own meme — their reaction is removed."""
    client, meme_capture = meme_event_env
    author = ut.guildObject.get_member(101)  # alice authored seeded meme 999001
    own = _meme_reaction(memeReview.goodMeme, count=1, users=[author])
    message = _meme_message(999001, author_id=101, reactions=[own])
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=101, message_id=999001, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    message.remove_reaction.assert_awaited_once()


async def test_add_meme_reactions_unhandled_emote_sends_error(meme_event_env):
    """A 'not a meme' react with no existing not-a-meme reaction falls through to the error notice."""
    client, meme_capture = meme_event_env
    message = _meme_message(999001)  # no reactions present
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.notMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_add", payload)
    await asyncio.sleep(0)

    assert "Error adding meme reaction (1)" in [m.content for m in meme_capture.messages]


# --- on_raw_reaction_remove → remove_meme_reactions ---


async def test_remove_meme_reactions_good_reaction_reduces_score(meme_event_env):
    """Removing a 'good meme' reaction reverses its score bump and the reactor's point."""
    client, meme_capture = meme_event_env
    message = _meme_message(999001, reactions=[_meme_reaction(memeReview.notMeme, count=1)])
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_remove", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999001"][0] == 8  # 10 - getScore(goodMeme)=2
    with shelve.open("./database/meme_leaderboard.db") as db:
        assert db["102"] == [29, 0]  # bob -1 for un-reacting (was [30, 0])


async def test_remove_meme_reactions_ignores_non_meme(meme_event_env):
    """A non-image embed short-circuits before any DB change."""
    client, meme_capture = meme_event_env
    message = _meme_message(999001, image_url="https://example.invalid/notes.txt")
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_remove", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999001"][0] == 10  # unchanged


async def test_remove_meme_reactions_not_meme_reaction_restores_daily(meme_event_env):
    """Removing the last 'not a meme' reaction un-flags the meme and restores the author's daily count."""
    client, meme_capture = meme_event_env
    with shelve.open("./database/meme_review.db") as db:
        db["999003"] = [5, False, 101, "https://example.invalid/meme3.png"]  # currently flagged not-a-meme
    message = _meme_message(999003, reactions=[_meme_reaction(memeReview.notMeme, count=1)])
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999003, emoji_name=memeReview.notMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_remove", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999003"][1] is True  # flipped back to "is a meme"
    with shelve.open("./database/meme_leaderboard.db") as db:
        assert db["101"] == [50, 1]  # alice's daily count restored


async def test_remove_meme_reactions_ignores_invalid_emote(meme_event_env):
    """A non-vote emoji is ignored before any fetch or DB change."""
    client, meme_capture = meme_event_env
    meme_capture.channel.fetch_message = AsyncMock(return_value=_meme_message(999001))
    payload = _reaction_payload(
        user_id=102, message_id=999001, emoji_name="randomemoji", channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_remove", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999001"][0] == 10  # unchanged


async def test_remove_meme_reactions_creates_entry_for_untracked_meme(meme_event_env):
    """Removing a reaction from a meme not yet in the DB creates its entry, then applies the change."""
    client, meme_capture = meme_event_env
    message = _meme_message(999009, reactions=[_meme_reaction(memeReview.notMeme, count=1)])  # not seeded
    meme_capture.channel.fetch_message = AsyncMock(return_value=message)
    payload = _reaction_payload(
        user_id=102, message_id=999009, emoji_name=memeReview.goodMeme, channel_id=meme_capture.channel.id
    )

    client.dispatch("raw_reaction_remove", payload)
    await asyncio.sleep(0)

    with shelve.open("./database/meme_review.db") as db:
        assert db["999009"][0] == -2  # created [0,...] then reduced by getScore(goodMeme)=2
