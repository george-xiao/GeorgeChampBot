from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import common.utils as ut
from components.movieNight import SUGGESTION_DATABASE
from components.subcomponents.movieNight import upcomingMovie
from components.subcomponents.movieNight.movie import Movie


# ---- MovieSuggestions: add ----

@pytest.mark.asyncio
async def test_movie_add_suggestion_success(db_dir, ut_globals, snap_send):
    embed = SUGGESTION_DATABASE.add_suggestion("alice", Movie("Dune", "Sci-Fi", "Sandworms"))
    await snap_send(embed, "movie/add-suggestion-success")


@pytest.mark.asyncio
async def test_movie_add_suggestion_at_capacity(db_dir, ut_globals, snap_send):
    # Pre-fill alice's list to capacity (MAX_SUGGESTIONS = 10)
    for i in range(10):
        SUGGESTION_DATABASE.add_suggestion("alice", Movie(f"Movie {i}", "Genre", f"Reason {i}"))
    embed = SUGGESTION_DATABASE.add_suggestion("alice", Movie("Overflow", "Drama", "Should fail"))
    await snap_send(embed, "movie/add-suggestion-at-capacity")


# ---- MovieSuggestions: list ----

@pytest.mark.asyncio
async def test_movie_list_suggestions_populated(seeded_movie_db, ut_globals, snap_send):
    await snap_send(SUGGESTION_DATABASE.get_list_embed(), "movie/list-suggestions-populated")


@pytest.mark.asyncio
async def test_movie_list_suggestions_empty(db_dir, ut_globals, snap_send):
    await snap_send(SUGGESTION_DATABASE.get_list_embed(), "movie/list-suggestions-empty")


# ---- MovieSuggestions: view ----

@pytest.mark.asyncio
async def test_movie_view_suggestion_found(seeded_movie_db, ut_globals, snap_send):
    await snap_send(SUGGESTION_DATABASE.get_suggestion_embed("alice", "Interstellar"), "movie/view-suggestion-found")


@pytest.mark.asyncio
async def test_movie_view_suggestion_not_found(seeded_movie_db, ut_globals, snap_send):
    await snap_send(SUGGESTION_DATABASE.get_suggestion_embed("alice", "Ghost Movie"), "movie/view-suggestion-not-found")


# ---- MovieSuggestions: remove ----

@pytest.mark.asyncio
async def test_movie_remove_suggestion_success(seeded_movie_db, ut_globals, snap_send):
    await snap_send(SUGGESTION_DATABASE.remove_suggestion("alice", "Inception"), "movie/remove-suggestion-success")


@pytest.mark.asyncio
async def test_movie_remove_suggestion_not_found(seeded_movie_db, ut_globals, snap_send):
    await snap_send(SUGGESTION_DATABASE.remove_suggestion("alice", "Ghost Movie"), "movie/remove-suggestion-not-found")


# ---- upcomingMovie helpers ----

def _make_scheduled_event(start_time=None):
    """Mock discord.ScheduledEvent."""
    event = MagicMock()
    event.start_time = start_time or datetime(2024, 6, 15, 20, 0, 0, tzinfo=timezone.utc)
    event.guild_id = 1000
    event.id = 99999
    event.status = discord.EventStatus.scheduled
    return event


# ---- view-upcoming ----

@pytest.mark.asyncio
async def test_movie_view_upcoming_no_event(db_dir, ut_globals, snap_send):
    error_embed = discord.Embed(colour=ut.embed_colour["ERROR"])
    error_embed.title = '"Movie Night" event does not exist!'
    error_embed.description = "Test error description"

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=error_embed)):
        result = await upcomingMovie.get_upcoming()

    await snap_send(result, "movie/view-upcoming-no-event")


@pytest.mark.asyncio
async def test_movie_view_upcoming_with_event(db_dir, ut_globals, snap_send):
    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=None)), \
         patch("common.utils.get_movie_event_link", new=AsyncMock(return_value="https://discord.com/events/1000/99999")):
        result = await upcomingMovie.get_upcoming()

    await snap_send(result, "movie/view-upcoming-with-event")


# ---- pick-host ----

@pytest.mark.asyncio
async def test_movie_pick_host_no_event(db_dir, ut_globals, snap_send):
    error_embed = discord.Embed(colour=ut.embed_colour["ERROR"])
    error_embed.title = '"Movie Night" event does not exist!'
    error_embed.description = "Event must exist"

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=error_embed)):
        embed = await upcomingMovie.set_host("alice")

    await snap_send(embed, "movie/pick-host-no-event")


@pytest.mark.asyncio
async def test_movie_pick_host_success(db_dir, ut_globals, snap_send):
    event = _make_scheduled_event()

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=None)), \
         patch("common.utils.get_movie_event", new=AsyncMock(return_value=event)), \
         patch("common.utils.convert_to_est_time", return_value="Jun 15, 04:00 PM EDT"), \
         patch.object(upcomingMovie, "start_pick_reminder"), \
         patch.object(upcomingMovie, "update_event_description"):
        embed = await upcomingMovie.set_host("alice")

    await snap_send(embed, "movie/pick-host-success")


# ---- pick-movie ----

@pytest.mark.asyncio
async def test_movie_pick_movie_no_event(db_dir, ut_globals, snap_send):
    error_embed = discord.Embed(colour=ut.embed_colour["ERROR"])
    error_embed.title = '"Movie Night" event does not exist!'
    error_embed.description = "Event must exist"

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=error_embed)):
        embed = await upcomingMovie.set_movie("alice", "Interstellar", SUGGESTION_DATABASE)

    await snap_send(embed, "movie/pick-movie-no-event")


@pytest.mark.asyncio
async def test_movie_pick_movie_no_host_set(seeded_movie_db, ut_globals, snap_send):
    """Event exists but no upcoming_host has been set yet."""
    event = _make_scheduled_event()

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=None)), \
         patch("common.utils.get_movie_event", new=AsyncMock(return_value=event)), \
         patch.object(upcomingMovie, "update_event_description"):
        embed = await upcomingMovie.set_movie("alice", "Interstellar", SUGGESTION_DATABASE)

    await snap_send(embed, "movie/pick-movie-no-host-set")


@pytest.mark.asyncio
async def test_movie_pick_movie_not_the_host(seeded_movie_db, ut_globals, snap_send):
    """Event exists, upcoming_host=bob, alice tries to pick. Should reject."""
    import shelve

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "bob"

    event = _make_scheduled_event()

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=None)), \
         patch("common.utils.get_movie_event", new=AsyncMock(return_value=event)), \
         patch.object(upcomingMovie, "update_event_description"):
        embed = await upcomingMovie.set_movie("alice", "Interstellar", SUGGESTION_DATABASE)

    await snap_send(embed, "movie/pick-movie-not-the-host")


@pytest.mark.asyncio
async def test_movie_pick_movie_movie_not_in_list(seeded_movie_db, ut_globals, snap_send):
    """Alice is host but picks a movie not in her suggestion list."""
    import shelve

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"

    event = _make_scheduled_event()

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=None)), \
         patch("common.utils.get_movie_event", new=AsyncMock(return_value=event)), \
         patch.object(upcomingMovie, "update_event_description"):
        embed = await upcomingMovie.set_movie("alice", "Ghost Film", SUGGESTION_DATABASE)

    await snap_send(embed, "movie/pick-movie-not-in-list")


@pytest.mark.asyncio
async def test_movie_pick_movie_success(seeded_movie_db, ut_globals, snap_send):
    """Alice is host, picks a movie from her list, should succeed."""
    import shelve

    with shelve.open(upcomingMovie.UPCOMING_MOVIE_NIGHT_DB_PATH) as db:
        db["upcoming_host_name"] = "alice"

    event = _make_scheduled_event()

    with patch("common.utils.movie_event_not_present", new=AsyncMock(return_value=None)), \
         patch("common.utils.get_movie_event", new=AsyncMock(return_value=event)), \
         patch("common.utils.convert_to_est_time", return_value="Jun 15, 04:00 PM EDT"), \
         patch.object(upcomingMovie, "update_event_description"):
        embed = await upcomingMovie.set_movie("alice", "Interstellar", SUGGESTION_DATABASE)

    await snap_send(embed, "movie/pick-movie-success")


# ---- bump_prev_host (used by pick-host slash command) ----

@pytest.mark.asyncio
async def test_movie_bump_prev_host_nonexistent(db_dir, ut_globals, snap_send):
    """When the previous host doesn't have any suggestions, bump should fail with an error embed."""
    prev_host = MagicMock()
    prev_host.name = "ghost"

    embed = SUGGESTION_DATABASE.bump_prev_host(prev_host)
    await snap_send(embed, "movie/bump-prev-host-nonexistent")
