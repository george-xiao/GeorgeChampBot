"""Integration tests for movie.

- Slash commands dispatch through `tree._call`.
- The `/movie add-suggestion` modal-submit path dispatches through the
  `SuggestionModal.on_submit` callback (Discord modals don't go through
  the command tree; this is their dispatch boundary).
- Scheduled-event gateway handlers (registered on `ut.client` at import
  time in `components/movieNight.py`) dispatch via `ut.client.dispatch`.
"""

import asyncio
import shelve
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import common.utils as ut
from commands.movie.add_suggestion import SuggestionModal
from components import movieNight  # noqa: F401 — import triggers on_scheduled_event_* registration
from components.movieNight import SUGGESTION_DATABASE
from components.subcomponents.movieNight import upcomingMovie, eventReminder
from tests._capture import CapturedMessages, make_capturing_interaction
from tests._dispatch import invoke_slash
from tests._factories import make_member


def _make_scheduled_event(start_time=None):
    # Default start_time is in the future: set_host refuses past-dated events
    event = MagicMock()
    event.start_time = start_time or datetime.now(timezone.utc) + timedelta(days=7)
    event.guild_id = 1000
    event.id = 99999
    event.status = discord.EventStatus.scheduled
    event.name = "Movie Night"
    event.description = ""
    event.edit = AsyncMock()
    return event


def _patch_event_present(monkeypatch, event=None):
    """Set up the 'a Movie Night event exists' state on ut.* helpers."""
    monkeypatch.setattr(ut, "movie_event_not_present", AsyncMock(return_value=None))
    monkeypatch.setattr(ut, "get_movie_event", AsyncMock(return_value=event or _make_scheduled_event()))
    monkeypatch.setattr(ut, "convert_to_est_time", lambda _t: "Jun 15, 04:00 PM EDT")
    # Side-effect helpers triggered by set_host/set_movie — silence them.
    monkeypatch.setattr(upcomingMovie, "update_event_description", lambda *a, **k: None)
    monkeypatch.setattr(upcomingMovie, "start_pick_reminder", lambda *a, **k: None)


def _patch_event_missing(monkeypatch):
    error_embed = discord.Embed(colour=ut.embed_colour["ERROR"])
    error_embed.title = '"Movie Night" event does not exist!'
    error_embed.description = "Event must exist"
    monkeypatch.setattr(ut, "movie_event_not_present", AsyncMock(return_value=error_embed))


# --- /movie list-suggestions ---

async def test_movie_list_suggestions_populated(seeded_movie_db, tree, guild, regular_member):
    capture = await invoke_slash(tree, "movie list-suggestions", regular_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    desc = msg.embed["description"]
    assert "Interstellar" in desc
    assert "Inception" in desc
    assert "Top Gun" in desc


async def test_movie_list_suggestions_empty(db_dir, tree, guild, regular_member):
    capture = await invoke_slash(tree, "movie list-suggestions", regular_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    assert "empty" in msg.embed["description"].lower()


# --- /movie view-suggestion ---

async def test_movie_view_suggestion_found(seeded_movie_db, tree, guild, regular_member):
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree, "movie view-suggestion", regular_member, guild,
        options={"user": alice, "movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "Interstellar" in msg.embed["description"]
    assert "Sci-Fi" in msg.embed["description"]


async def test_movie_view_suggestion_not_found(seeded_movie_db, tree, guild, regular_member):
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree, "movie view-suggestion", regular_member, guild,
        options={"user": alice, "movie_name": "Ghost Movie"},
    )
    [msg] = capture.messages
    assert "not found" in msg.embed["description"].lower()


# --- /movie remove-suggestion ---

async def test_movie_remove_suggestion_success(seeded_movie_db, tree, guild, regular_member):
    # regular_member is alice; she removes Inception from her own list.
    assert SUGGESTION_DATABASE.get_movie("alice", "Inception") is not None
    capture = await invoke_slash(
        tree, "movie remove-suggestion", regular_member, guild,
        options={"movie_name": "Inception"},
    )
    [msg] = capture.messages
    assert "Inception" in msg.embed["description"]
    assert SUGGESTION_DATABASE.get_movie("alice", "Inception") is None


async def test_movie_remove_suggestion_not_found(seeded_movie_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree, "movie remove-suggestion", regular_member, guild,
        options={"movie_name": "Ghost Movie"},
    )
    [msg] = capture.messages
    assert "not found" in msg.embed["description"].lower()


# --- /movie view-upcoming ---

async def test_movie_view_upcoming_no_event(db_dir, tree, guild, regular_member, monkeypatch):
    _patch_event_missing(monkeypatch)
    capture = await invoke_slash(tree, "movie view-upcoming", regular_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_view_upcoming_with_event(db_dir, tree, guild, regular_member, monkeypatch):
    _patch_event_present(monkeypatch)
    monkeypatch.setattr(ut, "get_movie_event_link", AsyncMock(return_value="https://discord.com/events/1000/99999"))
    capture = await invoke_slash(tree, "movie view-upcoming", regular_member, guild)
    [msg] = capture.messages
    assert "Click here" in msg.content
    assert "discord.com/events/1000/99999" in msg.content


# --- /movie pick-movie ---

async def test_movie_pick_movie_no_event(db_dir, tree, guild, regular_member, monkeypatch):
    _patch_event_missing(monkeypatch)
    capture = await invoke_slash(
        tree, "movie pick-movie", regular_member, guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_pick_movie_no_host_set(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    _patch_event_present(monkeypatch)
    capture = await invoke_slash(
        tree, "movie pick-movie", regular_member, guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "host" in msg.embed["title"].lower()
    assert "not been selected" in msg.embed["description"].lower()


async def test_movie_pick_movie_not_the_host(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "bob"
    _patch_event_present(monkeypatch)
    # regular_member is alice; bob is the host → alice gets rejected.
    capture = await invoke_slash(
        tree, "movie pick-movie", regular_member, guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "bob" in msg.embed["description"]


async def test_movie_pick_movie_not_in_list(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"
    _patch_event_present(monkeypatch)
    capture = await invoke_slash(
        tree, "movie pick-movie", regular_member, guild,
        options={"movie_name": "Ghost Film"},
    )
    [msg] = capture.messages
    assert "Ghost Film" in msg.embed["title"]
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_pick_movie_success(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"
    _patch_event_present(monkeypatch)
    capture = await invoke_slash(
        tree, "movie pick-movie", regular_member, guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "Interstellar" in msg.embed["description"]
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        picked = db.get("upcoming_movie")
    assert picked is not None and picked.name == "Interstellar"


# --- /admin movie pick-host ---

async def test_movie_pick_host_no_event(db_dir, tree, guild, admin_member, monkeypatch):
    _patch_event_missing(monkeypatch)
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree, "admin movie pick-host", admin_member, guild,
        options={"user": alice},
    )
    [msg] = capture.messages
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_pick_host_event_date_passed(db_dir, tree, guild, admin_member, monkeypatch):
    # A "Movie Night" event exists but its start time already passed (e.g. the
    # weekly event wasn't rescheduled) → set_host must refuse instead of arming
    # a pick reminder that would silently never fire.
    past_event = _make_scheduled_event(start_time=datetime.now(timezone.utc) - timedelta(days=1))
    _patch_event_present(monkeypatch, event=past_event)
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree, "admin movie pick-host", admin_member, guild,
        options={"user": alice},
    )
    [msg] = capture.messages
    assert "already passed" in msg.embed["title"].lower()
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        assert db.get("upcoming_host_name") is None


async def test_movie_pick_host_success(db_dir, tree, guild, admin_member, monkeypatch):
    _patch_event_present(monkeypatch)
    monkeypatch.setattr(ut, "get_member_str", lambda name: f"<@{name}>")
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree, "admin movie pick-host", admin_member, guild,
        options={"user": alice},
    )
    [msg] = capture.messages
    assert "host selected" in msg.embed["title"].lower()
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        assert db.get("upcoming_host_name") == "alice"


# --- Modal: /movie add-suggestion → SuggestionModal.on_submit ---

async def test_movie_add_suggestion_modal_submit_adds_to_db(db_dir, guild, regular_member):
    modal = SuggestionModal()
    modal.movie_name._value = "Dune"
    modal.movie_genre._value = "Sci-Fi"
    modal.movie_reason._value = "Sandworms"

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await modal.on_submit(interaction)

    [msg] = capture.messages
    assert msg.embed is not None
    assert SUGGESTION_DATABASE.get_movie("alice", "Dune") is not None


async def test_movie_add_suggestion_modal_at_capacity(db_dir, guild, regular_member):
    # Fill alice's list to MAX_SUGGESTIONS (10).
    from components.subcomponents.movieNight.movie import Movie
    for i in range(10):
        SUGGESTION_DATABASE.add_suggestion("alice", Movie(f"Movie {i}", "Genre", f"Reason {i}"))

    modal = SuggestionModal()
    modal.movie_name._value = "Overflow"
    modal.movie_genre._value = "Drama"
    modal.movie_reason._value = "Should fail"

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await modal.on_submit(interaction)

    [msg] = capture.messages
    assert msg.embed is not None
    assert SUGGESTION_DATABASE.get_movie("alice", "Overflow") is None


# --- Scheduled-event handlers ---

@pytest.fixture
def scheduled_event_bot(monkeypatch):
    """Patch the side-effect helpers the on_scheduled_event_* handlers call,
    so we can assert they're invoked without running the real bodies (which
    spawn AsyncTasks against ut.client's loop, edit ScheduledEvents, etc.)."""
    update_calls = []
    pick_reminder_calls = []
    reminder_calls = []
    monkeypatch.setattr(upcomingMovie, "update_event_description", lambda is_command: update_calls.append(is_command))
    monkeypatch.setattr(upcomingMovie, "start_pick_reminder", lambda: pick_reminder_calls.append(True))
    monkeypatch.setattr(eventReminder, "start_event_reminder", lambda: reminder_calls.append(True))
    return update_calls, pick_reminder_calls, reminder_calls


async def test_on_scheduled_event_create_triggers_update_and_reminders(scheduled_event_bot, ut_client_ready):
    update_calls, pick_reminder_calls, reminder_calls = scheduled_event_bot

    ut_client_ready.dispatch("scheduled_event_create", _make_scheduled_event())
    await asyncio.sleep(0)

    assert update_calls == [False]
    assert pick_reminder_calls == [True]
    assert reminder_calls == [True]


async def test_on_scheduled_event_update_skips_reminders_when_start_unchanged(scheduled_event_bot, ut_client_ready):
    update_calls, pick_reminder_calls, reminder_calls = scheduled_event_bot

    same = datetime(2024, 6, 15, 20, 0, 0, tzinfo=timezone.utc)
    old = _make_scheduled_event(start_time=same)
    new = _make_scheduled_event(start_time=same)
    ut_client_ready.dispatch("scheduled_event_update", old, new)
    await asyncio.sleep(0)

    assert update_calls == [False]
    # Same start_time → reminders aren't restarted.
    assert pick_reminder_calls == []
    assert reminder_calls == []


async def test_on_scheduled_event_update_restarts_reminders_when_start_changes(scheduled_event_bot, ut_client_ready):
    update_calls, pick_reminder_calls, reminder_calls = scheduled_event_bot

    old = _make_scheduled_event(start_time=datetime(2024, 6, 15, 20, 0, 0, tzinfo=timezone.utc))
    new = _make_scheduled_event(start_time=datetime(2024, 6, 16, 20, 0, 0, tzinfo=timezone.utc))
    ut_client_ready.dispatch("scheduled_event_update", old, new)
    await asyncio.sleep(0)

    assert update_calls == [False]
    assert pick_reminder_calls == [True]
    assert reminder_calls == [True]


async def test_on_scheduled_event_delete_triggers_update_and_reminders(scheduled_event_bot, ut_client_ready):
    update_calls, pick_reminder_calls, reminder_calls = scheduled_event_bot

    ut_client_ready.dispatch("scheduled_event_delete", _make_scheduled_event())
    await asyncio.sleep(0)

    assert update_calls == [False]
    assert pick_reminder_calls == [True]
    assert reminder_calls == [True]
