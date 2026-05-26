"""Background tests for movie-night reminders — event-soon ping + host pick nag (looptime)."""

import shelve
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import common.utils as ut
from components.subcomponents.movieNight import eventReminder, upcomingMovie
from components.subcomponents.movieNight.movie import Movie
from tests._capture import CapturedMessages, make_capturing_channel

pytestmark = [pytest.mark.looptime]


def _scheduled_event(start_time):
    event = MagicMock()
    event.start_time = start_time
    event.status = discord.EventStatus.scheduled
    return event


# === eventReminder.__remind_event_coroutine ===


async def test_event_reminder_pings_movie_role_when_event_near(monkeypatch):
    # Event 30 min out (inside the 1h reminder threshold) -> reminder fires now.
    event = _scheduled_event(datetime.now(timezone.utc) + timedelta(minutes=30))
    monkeypatch.setattr(ut, "get_movie_event", AsyncMock(return_value=event))
    monkeypatch.setattr(ut, "get_movie_event_link", AsyncMock(return_value="https://discord.com/events/1/2"))
    monkeypatch.setattr(ut, "get_role_str", lambda _: "<@&MOVIE>")
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "get_channel", lambda _: make_capturing_channel(capture))

    eventReminder.start_event_reminder()
    await eventReminder.EVENT_REMINDER_TASK.async_task

    [msg] = capture.messages
    assert "Movie night alert" in msg.content
    assert "<@&MOVIE>" in msg.content


async def test_event_reminder_skips_when_already_reminded(monkeypatch):
    import pickle

    event = _scheduled_event(datetime.now(timezone.utc) + timedelta(minutes=30))
    # Mark this exact start_time as already reminded.
    with open(eventReminder.LAST_EVENT_PATH, "wb") as f:
        pickle.dump(event.start_time, f)

    monkeypatch.setattr(ut, "get_movie_event", AsyncMock(return_value=event))
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "get_channel", lambda _: make_capturing_channel(capture))

    eventReminder.start_event_reminder()
    await eventReminder.EVENT_REMINDER_TASK.async_task

    assert capture.messages == []


async def test_event_reminder_skips_when_no_event(monkeypatch):
    monkeypatch.setattr(ut, "get_movie_event", AsyncMock(return_value=None))
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "get_channel", lambda _: make_capturing_channel(capture))

    eventReminder.start_event_reminder()
    await eventReminder.EVENT_REMINDER_TASK.async_task

    assert capture.messages == []


# === upcomingMovie.__remind_host_coroutine ===


async def test_pick_reminder_nags_host_then_stops_once_movie_picked(monkeypatch):
    event = _scheduled_event(datetime.now(timezone.utc) + timedelta(days=2))
    monkeypatch.setattr(ut, "get_movie_event", AsyncMock(return_value=event))
    monkeypatch.setattr(ut, "get_member_str", lambda name: f"<@{name}>")
    monkeypatch.setattr(ut, "convert_to_est_time", lambda t: "soon")

    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    base_send = channel.send

    async def send_then_pick(*args, **kwargs):
        # After the nag is sent, the host "picks" a movie so the next loop
        # iteration's guard is False and the task terminates (no infinite loop).
        msg = await base_send(*args, **kwargs)
        with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
            db["upcoming_movie"] = Movie("Dune", "Sci-Fi", "picked")
        return msg

    channel.send = send_then_pick
    monkeypatch.setattr(ut, "get_channel", lambda _: channel)

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"  # host set, no movie yet

    upcomingMovie.start_pick_reminder()
    await upcomingMovie.PICK_REMINDER_TASK.async_task

    [msg] = capture.messages
    assert "please select the upcoming movie" in msg.embed["title"].lower()


async def test_pick_reminder_skips_when_movie_already_picked(monkeypatch):
    event = _scheduled_event(datetime.now(timezone.utc) + timedelta(days=2))
    monkeypatch.setattr(ut, "get_movie_event", AsyncMock(return_value=event))
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "get_channel", lambda _: make_capturing_channel(capture))

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"
        db["upcoming_movie"] = Movie("Dune", "Sci-Fi", "already picked")

    upcomingMovie.start_pick_reminder()
    await upcomingMovie.PICK_REMINDER_TASK.async_task

    assert capture.messages == []
