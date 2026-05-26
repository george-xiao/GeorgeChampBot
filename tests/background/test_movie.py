"""Background tests for movie — scheduled-event gateway handlers trigger real AsyncTasks (looptime)."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import common.utils as ut
from components import movieNight  # noqa: F401 — registers on_scheduled_event_* handlers
from tests._capture import CapturedMessages, make_capturing_channel

pytestmark = [pytest.mark.looptime]


@pytest.fixture
async def event_bot(ut_client_ready, guild, monkeypatch):
    """Boot ut.client with a fake scheduled event on the guild."""
    event = MagicMock()
    event.start_time = datetime(2024, 6, 15, 20, 0, 0, tzinfo=timezone.utc)
    event.guild_id = 1000
    event.id = 99999
    event.status = discord.EventStatus.scheduled
    event.name = "Movie Night"
    event.description = ""
    event.edit = AsyncMock()

    monkeypatch.setattr(ut.guildObject, "scheduled_events", [event])
    monkeypatch.setattr(ut.guildObject, "fetch_scheduled_events", AsyncMock(return_value=[event]))
    return ut_client_ready, event


async def test_on_scheduled_event_create_updates_event_description(event_bot):
    """on_scheduled_event_create triggers update_event_description which edits the event."""
    client, event = event_bot

    client.dispatch("scheduled_event_create", event)
    await asyncio.sleep(0.1)  # let AsyncTask run

    event.edit.assert_awaited_once()


async def test_on_scheduled_event_update_skips_when_start_unchanged(event_bot):
    """Same start_time → update runs but reminder is not restarted."""
    client, event = event_bot

    old = MagicMock()
    old.start_time = event.start_time
    client.dispatch("scheduled_event_update", old, event)
    await asyncio.sleep(0.1)

    # update_event_description still fires (edits event)
    event.edit.assert_awaited_once()


async def test_on_scheduled_event_update_restarts_when_start_changes(event_bot, monkeypatch):
    """Different start_time → both update and reminder restart."""
    client, event = event_bot

    old = MagicMock()
    old.start_time = datetime(2024, 6, 14, 20, 0, 0, tzinfo=timezone.utc)  # different
    client.dispatch("scheduled_event_update", old, event)
    await asyncio.sleep(0.1)

    event.edit.assert_awaited_once()


async def test_on_scheduled_event_delete_notifies_when_event_missing(event_bot, monkeypatch):
    """With the event gone, update_event_description finds no event and posts the
    "event does not exist" notification to the movie channel (it does not edit)."""
    client, event = event_bot

    # After delete, no event exists
    monkeypatch.setattr(ut.guildObject, "scheduled_events", [])
    monkeypatch.setattr(ut.guildObject, "fetch_scheduled_events", AsyncMock(return_value=[]))

    capture = CapturedMessages()
    monkeypatch.setattr(ut, "get_channel", lambda _: make_capturing_channel(capture))

    client.dispatch("scheduled_event_delete", event)
    await asyncio.sleep(0.1)  # looptime drains the (sleep-free) task before waking

    event.edit.assert_not_awaited()
    [msg] = capture.messages
    assert "does not exist" in msg.embed["title"].lower()
