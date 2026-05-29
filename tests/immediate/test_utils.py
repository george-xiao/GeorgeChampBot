"""Tests for common.utils helpers
Helpers: send_react_msg

Verifies the bot posts to mainChannel and reacts with a matching guild emoji (or skips reacting when none matches).
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
