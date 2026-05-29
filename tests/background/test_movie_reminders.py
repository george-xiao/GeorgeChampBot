"""Background tests for movie-night reminders — event-soon ping + host pick nag (looptime)."""

import shelve
from datetime import datetime, timedelta, timezone

import pytest

import common.utils as ut
from components.subcomponents.movieNight import eventReminder, upcomingMovie
from components.subcomponents.movieNight.movie import Movie
from tests._stubs import make_scheduled_event, patch_channel, patch_movie_event_missing, patch_movie_event_present

pytestmark = [pytest.mark.looptime]


# --- eventReminder.__remind_event_coroutine ---


async def test_event_reminder_pings_movie_role_when_event_near(guild, monkeypatch):
    # Event 30 min out (inside the 1h reminder threshold) -> reminder fires now.
    event = make_scheduled_event(start_time=datetime.now(timezone.utc) + timedelta(minutes=30))
    patch_movie_event_present(monkeypatch, event=event)
    capture = patch_channel(monkeypatch, ut.env["MOVIE_CHANNEL"])

    eventReminder.start_event_reminder()
    await eventReminder.EVENT_REMINDER_TASK.async_task

    [msg] = capture.messages
    assert "Movie night alert" in msg.content
    assert "<@&2002>" in msg.content  # MOVIE role id from make_movie_role


async def test_event_reminder_skips_when_already_reminded(guild, monkeypatch):
    import pickle

    event = make_scheduled_event(start_time=datetime.now(timezone.utc) + timedelta(minutes=30))
    # Mark this exact start_time as already reminded.
    with open(eventReminder.LAST_EVENT_PATH, "wb") as f:
        pickle.dump(event.start_time, f)

    patch_movie_event_present(monkeypatch, event=event)
    capture = patch_channel(monkeypatch, ut.env["MOVIE_CHANNEL"])

    eventReminder.start_event_reminder()
    await eventReminder.EVENT_REMINDER_TASK.async_task

    assert capture.messages == []


async def test_event_reminder_skips_when_no_event(guild, monkeypatch):
    patch_movie_event_missing(monkeypatch)
    capture = patch_channel(monkeypatch, ut.env["MOVIE_CHANNEL"])

    eventReminder.start_event_reminder()
    await eventReminder.EVENT_REMINDER_TASK.async_task

    assert capture.messages == []


# --- upcomingMovie.__remind_host_coroutine ---


async def test_pick_reminder_nags_host_then_stops_once_movie_picked(guild, monkeypatch):
    event = make_scheduled_event(start_time=datetime.now(timezone.utc) + timedelta(days=2))
    patch_movie_event_present(monkeypatch, event=event)

    capture = patch_channel(monkeypatch, ut.env["MOVIE_CHANNEL"])
    base_send = capture.channel.send

    async def send_then_pick(*args, **kwargs):
        # After the nag is sent, the host "picks" a movie so the next loop
        # iteration's guard is False and the task terminates (no infinite loop).
        msg = await base_send(*args, **kwargs)
        with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
            db["upcoming_movie"] = Movie("Dune", "Sci-Fi", "picked")
        return msg

    capture.channel.send = send_then_pick

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"  # host set, no movie yet

    upcomingMovie.start_pick_reminder()
    await upcomingMovie.PICK_REMINDER_TASK.async_task

    [msg] = capture.messages
    assert "please select the upcoming movie" in msg.embed["title"].lower()
    assert "<@101>" in msg.embed["title"]  # alice's id from DEFAULT_MEMBERS


async def test_pick_reminder_skips_when_movie_already_picked(guild, monkeypatch):
    event = make_scheduled_event(start_time=datetime.now(timezone.utc) + timedelta(days=2))
    patch_movie_event_present(monkeypatch, event=event)
    capture = patch_channel(monkeypatch, ut.env["MOVIE_CHANNEL"])

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"
        db["upcoming_movie"] = Movie("Dune", "Sci-Fi", "already picked")

    upcomingMovie.start_pick_reminder()
    await upcomingMovie.PICK_REMINDER_TASK.async_task

    assert capture.messages == []
