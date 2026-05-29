"""Tests for autocomplete
Autocomplete: dota player
              emote (active + deleted)
              twitch streamer
              movie suggestion

Verifies each callback filters its choices to the relevant tracked, active, or invoking-user entries.
"""

from unittest.mock import MagicMock

from components import dotaReplay, emoteLeaderboard, movieNight, twitchAnnouncement


# --- tracked_dota_player_autocomplete ---


async def test_dota_autocomplete_filters_tracked_players(seeded_dota_db):
    choices = await dotaReplay.tracked_dota_player_autocomplete(MagicMock(), "ali")
    assert [c.value for c in choices] == ["12345"]  # alice, not bob
    assert "alice" in choices[0].name


# --- active_emote_autocomplete ---


async def test_active_emote_autocomplete_excludes_deleted(seeded_emote_db):
    choices = await emoteLeaderboard.active_emote_autocomplete(MagicMock(), "kek")
    names = [c.name for c in choices]
    assert "kekw" in names
    assert "oldmeme" not in names  # oldmeme is soft-deleted in the seed


# --- deleted_emote_autocomplete ---


async def test_deleted_emote_autocomplete_only_deleted(seeded_emote_db):
    choices = await emoteLeaderboard.deleted_emote_autocomplete(MagicMock(), "old")
    assert [c.value for c in choices] == ["oldmeme"]
    assert "deleted" in choices[0].name.lower()


# --- tracked_twitch_streamer_autocomplete ---


async def test_twitch_autocomplete_filters_tracked_streamers(seeded_twitch_db):
    choices = await twitchAnnouncement.tracked_twitch_streamer_autocomplete(MagicMock(), "alice")
    assert [c.value for c in choices] == ["alicestream"]


# --- movie_names_autocomplete ---


async def test_movie_autocomplete_filters_invoking_users_suggestions(seeded_movie_db):
    interaction = MagicMock()
    interaction.namespace.user = None  # no explicit user → fall back to caller
    interaction.user.name = "alice"

    choices = await movieNight.movie_names_autocomplete(interaction, "inter")
    assert [c.value for c in choices] == ["Interstellar"]
