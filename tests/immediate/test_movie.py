"""Tests for movie commands, modal submission, and scheduled-event gateway handlers."""

import shelve

from commands.movie.add_suggestion import SuggestionModal
from components import movieNight  # noqa: F401 — import triggers on_scheduled_event_* registration
from components.movieNight import SUGGESTION_DATABASE
from components.subcomponents.movieNight import upcomingMovie
from tests._capture import CapturedMessages, make_capturing_interaction
from tests._dispatch import invoke_slash
from tests._factories import make_member
from tests._stubs import patch_movie_event_missing, patch_movie_event_present


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
    # regular_member is alice; she views her own suggestions.
    capture = await invoke_slash(
        tree,
        "movie view-suggestion",
        regular_member,
        guild,
        options={"user": regular_member, "movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "Interstellar" in msg.embed["description"]
    assert "Sci-Fi" in msg.embed["description"]


async def test_movie_view_suggestion_not_found(seeded_movie_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "movie view-suggestion",
        regular_member,
        guild,
        options={"user": regular_member, "movie_name": "Ghost Movie"},
    )
    [msg] = capture.messages
    assert "not found" in msg.embed["description"].lower()


# --- /movie remove-suggestion ---


async def test_movie_remove_suggestion_success(seeded_movie_db, tree, guild, regular_member):
    # regular_member is alice; she removes Inception from her own list.
    assert SUGGESTION_DATABASE.get_movie("alice", "Inception") is not None
    capture = await invoke_slash(
        tree,
        "movie remove-suggestion",
        regular_member,
        guild,
        options={"movie_name": "Inception"},
    )
    [msg] = capture.messages
    assert "Inception" in msg.embed["description"]
    assert SUGGESTION_DATABASE.get_movie("alice", "Inception") is None


async def test_movie_remove_suggestion_not_found(seeded_movie_db, tree, guild, regular_member):
    capture = await invoke_slash(
        tree,
        "movie remove-suggestion",
        regular_member,
        guild,
        options={"movie_name": "Ghost Movie"},
    )
    [msg] = capture.messages
    assert "not found" in msg.embed["description"].lower()


# --- /movie view-upcoming ---


async def test_movie_view_upcoming_no_event(db_dir, tree, guild, regular_member, monkeypatch):
    patch_movie_event_missing(monkeypatch)
    capture = await invoke_slash(tree, "movie view-upcoming", regular_member, guild)
    [msg] = capture.messages
    assert msg.embed is not None
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_view_upcoming_with_event(db_dir, tree, guild, regular_member, monkeypatch):
    patch_movie_event_present(monkeypatch)
    capture = await invoke_slash(tree, "movie view-upcoming", regular_member, guild)
    [msg] = capture.messages
    assert "Click here" in msg.content
    assert "discord.com/events/1000/99999" in msg.content


# --- /movie pick-movie ---


async def test_movie_pick_movie_no_event(db_dir, tree, guild, regular_member, monkeypatch):
    patch_movie_event_missing(monkeypatch)
    capture = await invoke_slash(
        tree,
        "movie pick-movie",
        regular_member,
        guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_pick_movie_no_host_set(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    patch_movie_event_present(monkeypatch)
    capture = await invoke_slash(
        tree,
        "movie pick-movie",
        regular_member,
        guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "host" in msg.embed["title"].lower()
    assert "not been selected" in msg.embed["description"].lower()


async def test_movie_pick_movie_not_the_host(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "bob"
    patch_movie_event_present(monkeypatch)
    # regular_member is alice; bob is the host → alice gets rejected.
    capture = await invoke_slash(
        tree,
        "movie pick-movie",
        regular_member,
        guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "bob" in msg.embed["description"]


async def test_movie_pick_movie_not_in_list(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"
    patch_movie_event_present(monkeypatch)
    capture = await invoke_slash(
        tree,
        "movie pick-movie",
        regular_member,
        guild,
        options={"movie_name": "Ghost Film"},
    )
    [msg] = capture.messages
    assert "Ghost Film" in msg.embed["title"]
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_pick_movie_success(seeded_movie_db, tree, guild, regular_member, monkeypatch):
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"
    patch_movie_event_present(monkeypatch)
    capture = await invoke_slash(
        tree,
        "movie pick-movie",
        regular_member,
        guild,
        options={"movie_name": "Interstellar"},
    )
    [msg] = capture.messages
    assert "Interstellar" in msg.embed["description"]
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        picked = db.get("upcoming_movie")
    assert picked is not None and picked.name == "Interstellar"


# --- /admin movie pick-host ---


async def test_movie_pick_host_no_event(db_dir, tree, guild, admin_member, monkeypatch):
    patch_movie_event_missing(monkeypatch)
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree,
        "admin movie pick-host",
        admin_member,
        guild,
        options={"user": alice},
    )
    [msg] = capture.messages
    assert "does not exist" in msg.embed["title"].lower()


async def test_movie_pick_host_success(db_dir, tree, guild, admin_member, monkeypatch):
    patch_movie_event_present(monkeypatch)
    alice = make_member(101, "alice", nick="Alice the Great")
    capture = await invoke_slash(
        tree,
        "admin movie pick-host",
        admin_member,
        guild,
        options={"user": alice},
    )
    [msg] = capture.messages
    assert "host selected" in msg.embed["title"].lower()
    assert "<@101>" in msg.embed["description"]  # alice's id from DEFAULT_MEMBERS
    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        assert db.get("upcoming_host_name") == "alice"


async def test_movie_pick_host_prev_host_not_in_list(db_dir, tree, guild, admin_member, monkeypatch):
    new_host = make_member(102, "bob")
    prev = make_member(103, "carol")  # in guild, but no seeded suggestions → bump fails
    capture = await invoke_slash(
        tree,
        "admin movie pick-host",
        admin_member,
        guild,
        options={"user": new_host, "prev_host": prev},
    )
    [msg] = capture.messages
    assert "does not exist in suggestion list" in msg.embed["description"].lower()
    assert "<@103>" in msg.embed["description"]  # carol's id from DEFAULT_MEMBERS


async def test_movie_pick_host_prev_host_bumped(seeded_movie_db, tree, guild, admin_member, monkeypatch):
    patch_movie_event_present(monkeypatch)
    new_host = make_member(102, "bob")
    prev = make_member(101, "alice")  # alice has seeded suggestions → bump succeeds
    capture = await invoke_slash(
        tree,
        "admin movie pick-host",
        admin_member,
        guild,
        options={"user": new_host, "prev_host": prev},
    )
    [msg] = capture.messages
    assert "host selected" in msg.embed["title"].lower()
    assert "bumped to the end" in msg.embed["description"].lower()
    assert "<@101>" in msg.embed["description"]  # alice's id from DEFAULT_MEMBERS


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
