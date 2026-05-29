"""Background tests for movie
Events: on_scheduled_event_create (triggers AsyncTask)
        on_scheduled_event_update (triggers AsyncTask)
        on_scheduled_event_delete (triggers AsyncTask)

Verifies event description updates, reminder restarts on reschedule, and deletion notifications.
"""

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

import common.utils as ut
from components import movieNight  # noqa: F401 — registers on_scheduled_event_* handlers
from tests._stubs import patch_channel, patch_movie_event_missing, patch_movie_event_present


pytestmark = [pytest.mark.looptime]


@pytest.fixture
async def event_bot(ut_client_ready, guild, monkeypatch):
    """Boot ut.client with a fake scheduled event on the guild."""
    event = patch_movie_event_present(monkeypatch)
    return ut_client_ready, event


# --- on_scheduled_event_create → update event description ---


async def test_on_scheduled_event_create_updates_event_description(event_bot):
    """on_scheduled_event_create triggers update_event_description which edits the event."""
    client, event = event_bot

    client.dispatch("scheduled_event_create", event)
    await asyncio.sleep(0.1)  # let AsyncTask run

    event.edit.assert_awaited_once()


# --- on_scheduled_event_update → update + restart reminder on reschedule ---


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
    old.start_time = event.start_time - timedelta(days=1)  # different from event's start_time
    client.dispatch("scheduled_event_update", old, event)
    await asyncio.sleep(0.1)

    event.edit.assert_awaited_once()


# --- on_scheduled_event_delete → notify when event gone ---


async def test_on_scheduled_event_delete_notifies_when_event_missing(event_bot, monkeypatch):
    """With the event gone, update_event_description finds no event and posts the
    "event does not exist" notification to the movie channel (it does not edit)."""
    client, event = event_bot

    patch_movie_event_missing(monkeypatch)  # event gone after delete
    capture = patch_channel(monkeypatch, ut.env["MOVIE_CHANNEL"])

    client.dispatch("scheduled_event_delete", event)
    await asyncio.sleep(0.1)  # looptime drains the (sleep-free) task before waking

    event.edit.assert_not_awaited()
    [msg] = capture.messages
    assert "does not exist" in msg.embed["title"].lower()
