"""Integration tests for member join/leave gateway events.

Both handlers dispatch through `ut.client.dispatch` and exercise the `@ut.client.event`-registered handlers in GeorgeChampBot.py.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import common.utils as ut
import GeorgeChampBot  # noqa: F401 — module-level @ut.client.event registers handlers on ut.client
from tests._capture import CapturedMessages, make_capturing_channel


@pytest.fixture
def captured_main_channel(monkeypatch):
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "mainChannel", make_capturing_channel(capture))
    return capture


# --- on_member_join ---


async def test_on_member_join_welcomes_and_assigns_role(ut_client_ready, captured_main_channel, monkeypatch):
    welcome_role = MagicMock()
    welcome_role.name = "WELCOME"
    monkeypatch.setattr(ut, "get_role", lambda _name: welcome_role)

    matching_role = MagicMock()
    matching_role.name = "WELCOME"

    member = MagicMock()
    member.id = 999
    member.add_roles = AsyncMock()
    member.guild = MagicMock()
    member.guild.roles = [matching_role]

    ut_client_ready.dispatch("member_join", member)
    await asyncio.sleep(0)

    # Only the welcome message lands in mainChannel — no error fallback,
    # proving the role-assignment branch completed without raising.
    [msg] = captured_main_channel.messages
    assert "Welcome" in msg.content
    assert "<@999>" in msg.content


# --- on_member_remove ---


async def test_on_member_remove_sends_farewell(ut_client_ready, captured_main_channel):
    member = MagicMock()
    member.name = "alice"

    ut_client_ready.dispatch("member_remove", member)
    await asyncio.sleep(0)

    [msg] = captured_main_channel.messages
    assert "alice" in msg.content
    assert "leave us" in msg.content


# --- Error paths ---


async def test_on_member_join_error_path_sends_error_message(ut_client_ready, captured_main_channel, monkeypatch):
    welcome_role = MagicMock()
    welcome_role.name = "WELCOME"
    monkeypatch.setattr(ut, "get_role", lambda _name: welcome_role)

    matching_role = MagicMock()
    matching_role.name = "WELCOME"

    member = MagicMock()
    member.id = 999
    member.add_roles = AsyncMock(side_effect=RuntimeError("API failure"))
    member.guild = MagicMock()
    member.guild.roles = [matching_role]

    ut_client_ready.dispatch("member_join", member)
    await asyncio.sleep(0)

    # Welcome posts first, then the role-assignment failure triggers the except branch.
    welcome, error = captured_main_channel.messages
    assert "Welcome" in welcome.content
    assert "Error With On Member Join Event" in error.content
    assert "API failure" in error.content


async def test_on_member_remove_error_path_sends_error_message(ut_client_ready, monkeypatch):
    # Make the first mainChannel.send raise, the second succeed — exercises
    # the handler's except branch (which itself awaits mainChannel.send).
    captured_after_failure = []

    async def _send(content="", **kwargs):
        if not captured_after_failure and content and "decided to leave us" in content:
            raise RuntimeError("first send fails")
        captured_after_failure.append(content)

    channel = MagicMock()
    channel.send = _send
    monkeypatch.setattr(ut, "mainChannel", channel)

    member = MagicMock()
    member.name = "alice"

    ut_client_ready.dispatch("member_remove", member)
    await asyncio.sleep(0)

    [error_content] = captured_after_failure
    assert "Error With On Member Remove Event" in error_content
    assert "first send fails" in error_content
