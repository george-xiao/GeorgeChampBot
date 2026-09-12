"""Tests for common.utils helpers
Helpers: send_react_msg, get_role_str

Verifies the bot posts to mainChannel and reacts with a matching guild emoji (or skips reacting when none matches),
and that a missing role degrades to None instead of raising.
"""

import common.utils as ut
from tests._factories import make_emoji
from tests._stubs import patch_main_channel


# --- send_react_msg ---


async def test_send_react_msg_reacts_with_matching_emoji(guild, monkeypatch):
    capture = patch_main_channel(monkeypatch)
    monkeypatch.setattr(ut.guildObject, "emojis", [make_emoji("georgechamp", 555)])

    await ut.send_react_msg("reporting for duty", "georgechamp")

    [msg] = capture.messages
    assert msg.content == "reporting for duty"
    [sent] = capture.sent
    sent.add_reaction.assert_awaited_once_with("georgechamp:555")  # name:id of the matched emoji


async def test_send_react_msg_skips_reaction_when_no_emoji_matches(guild, monkeypatch):
    capture = patch_main_channel(monkeypatch)
    monkeypatch.setattr(ut.guildObject, "emojis", [make_emoji("somethingelse", 556)])

    await ut.send_react_msg("hello", "georgechamp")

    [msg] = capture.messages
    assert msg.content == "hello"
    [sent] = capture.sent
    sent.add_reaction.assert_not_awaited()  # no matching emoji → no reaction


# --- get_role_str ---


def test_get_role_str_mentions_an_existing_role(guild):
    """Guards the branch the fix moved `.id` into."""
    assert ut.get_role_str("ADMIN_ROLE") == "<@&2001>"  # id from make_admin_role


def test_get_role_str_returns_none_when_role_missing(guild, monkeypatch):
    """Regression: `get_role(...).id` raised AttributeError on None, because the walrus
    evaluates its whole right-hand side before testing truthiness -- so the branch written
    to report a missing role could never run."""
    monkeypatch.setattr(ut.guildObject, "roles", [])

    assert ut.get_role_str("ADMIN_ROLE") is None
