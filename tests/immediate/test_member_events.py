"""Tests for member events
Events: on_member_join
        on_member_remove

Verifies join welcome/role assignment, leave farewell, and error-path reporting for both.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from tests._stubs import patch_main_channel


# --- on_member_join → welcome + assign role ---


async def test_on_member_join_welcomes_and_assigns_role(ut_client_ready, monkeypatch):
    capture = patch_main_channel(monkeypatch)
    welcome_role = ut.get_role(ut.env["WELCOME_ROLE"])

    member = MagicMock()
    member.id = 999
    member.add_roles = AsyncMock()
    member.guild = ut.guildObject

    ut_client_ready.dispatch("member_join", member)
    await asyncio.sleep(0)

    # Welcome message lands; no error fallback (only one message in capture).
    [msg] = capture.messages
    assert "Welcome" in msg.content
    assert "<@999>" in msg.content
    member.add_roles.assert_awaited_once_with(welcome_role)


# --- on_member_remove → farewell ---


async def test_on_member_remove_sends_farewell(ut_client_ready, monkeypatch):
    capture = patch_main_channel(monkeypatch)
    member = MagicMock()
    member.name = "alice"

    ut_client_ready.dispatch("member_remove", member)
    await asyncio.sleep(0)

    [msg] = capture.messages
    assert "alice" in msg.content
    assert "leave us" in msg.content


# --- Error paths ---


async def test_on_member_join_error_path_sends_error_message(ut_client_ready, monkeypatch):
    capture = patch_main_channel(monkeypatch)
    welcome_role = ut.get_role(ut.env["WELCOME_ROLE"])

    member = MagicMock()
    member.id = 999
    member.add_roles = AsyncMock(side_effect=RuntimeError("API failure"))
    member.guild = ut.guildObject

    ut_client_ready.dispatch("member_join", member)
    await asyncio.sleep(0)

    # Welcome posts first, then the role-assignment failure triggers the except branch.
    welcome, error = capture.messages
    assert "Welcome" in welcome.content
    assert "Error With On Member Join Event" in error.content
    assert "API failure" in error.content
    # The assignment was attempted (with the right role) before raising.
    member.add_roles.assert_awaited_once_with(welcome_role)


async def test_on_member_remove_error_path_sends_error_message(ut_client_ready, monkeypatch):
    # Make the farewell send raise — exercises the handler's except branch,
    # which itself awaits mainChannel.send for the error message.
    capture = patch_main_channel(monkeypatch)
    base_send = capture.channel.send

    async def _send(content="", **kwargs):
        if "decided to leave us" in content:
            raise RuntimeError("first send fails")
        await base_send(content=content, **kwargs)

    capture.channel.send = _send

    member = MagicMock()
    member.name = "alice"

    ut_client_ready.dispatch("member_remove", member)
    await asyncio.sleep(0)

    [error_msg] = capture.messages
    assert "Error With On Member Remove Event" in error_msg.content
    assert "first send fails" in error_msg.content
