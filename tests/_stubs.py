"""External API stubs. Call with monkeypatch to fake network dependencies.

Use `stub_dota_api(monkeypatch, matches=[...])` for Dota/OpenDota.
Use `stub_twitch_api(monkeypatch, live_streams=[...])` for Twitch.
Use `stub_youtube(monkeypatch, search_video_id="...")` for YouTube/yt-dlp.
Use `patch_movie_event_present/missing(monkeypatch, ...)` for movie-night ScheduledEvent.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import discord

import common.utils as ut
from components import musicPlayer, twitchAnnouncement
from tests._capture import CapturedMessages, make_capturing_channel


# --- Discord channels ---


def patch_bot_channel(monkeypatch) -> CapturedMessages:
    """Patch ut.botChannel with a capturing channel; return the CapturedMessages for assertions."""
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "botChannel", make_capturing_channel(capture))
    return capture


def patch_main_channel(monkeypatch) -> CapturedMessages:
    """Patch ut.mainChannel with a capturing channel; return the CapturedMessages for assertions."""
    capture = CapturedMessages()
    monkeypatch.setattr(ut, "mainChannel", make_capturing_channel(capture))
    return capture


def patch_channel(monkeypatch, channel_name: str) -> CapturedMessages:
    """Prepend a capturing channel named `channel_name` to guildObject.channels so ut.get_channel(channel_name) resolves it.
    Library-boundary patch — exercises the real get_channel lookup."""
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    channel.name = channel_name
    monkeypatch.setattr(ut.guildObject, "channels", [channel, *ut.guildObject.channels])
    return capture


# --- Movie scheduled events ---


def make_scheduled_event(start_time=None):
    """Build a fake discord.ScheduledEvent for movie-night tests."""
    event = MagicMock()
    event.start_time = start_time or datetime(2024, 6, 15, 20, 0, 0, tzinfo=timezone.utc)
    event.guild_id = 1000
    event.id = 99999
    event.status = discord.EventStatus.scheduled
    event.name = "Movie Night"
    event.description = ""
    event.edit = AsyncMock()
    return event


def patch_movie_event_present(monkeypatch, event=None):
    """Stub guildObject.scheduled_events so ut.get_movie_event() finds an event."""
    ev = event or make_scheduled_event()
    monkeypatch.setattr(ut.guildObject, "scheduled_events", [ev])
    monkeypatch.setattr(ut.guildObject, "fetch_scheduled_events", AsyncMock(return_value=[ev]))
    return ev


def patch_movie_event_missing(monkeypatch):
    """Stub guildObject.scheduled_events so ut.get_movie_event() returns None."""
    monkeypatch.setattr(ut.guildObject, "scheduled_events", [])
    monkeypatch.setattr(ut.guildObject, "fetch_scheduled_events", AsyncMock(return_value=[]))


# --- Dota / OpenDota ---


def stub_dota_api(monkeypatch, *, matches=None, broken=False):
    """Patch ut.async_get_request to return Dota match data (or empty).
    broken=True simulates an API failure (returns None for every request)."""

    async def fake_get(url, headers=None):
        if broken:
            return None
        if "/recentMatches" in url:
            return matches if matches is not None else []
        return []

    monkeypatch.setattr(ut, "async_get_request", fake_get)


# --- Twitch ---


def stub_twitch_api(monkeypatch, *, live_streams=None, valid_users=None):
    """Patch ut.async_get_request and ut.async_post_request to mimic Twitch (valid_users=None accepts any login)."""
    # Twitch caches OAuth + livestreams at module scope; reset so prior tests don't leak.
    monkeypatch.setattr(twitchAnnouncement, "twitch_OAuth_token", None)
    monkeypatch.setattr(twitchAnnouncement, "twitch_curr_livestreams", {})

    async def fake_get(url, headers=None):
        if "id.twitch.tv/oauth2/validate" in url:
            return {"status": 200}
        if "api.twitch.tv/helix/users" in url:
            name = url.rsplit("login=", 1)[-1]
            if valid_users is None or name in valid_users:
                return {"data": [{"login": name, "id": "12345"}]}
            return {"data": []}
        if "api.twitch.tv/helix/streams" in url:
            return {"data": list(live_streams or [])}
        return None

    async def fake_post(url, body):
        if "id.twitch.tv/oauth2/token" in url:
            return {"access_token": "test-token", "expires_in": 3600}
        return None

    monkeypatch.setattr(ut, "async_get_request", fake_get)
    monkeypatch.setattr(ut, "async_post_request", fake_post)


# --- YouTube / yt-dlp ---


def stub_youtube(monkeypatch, *, search_video_id=None, video_meta=None, ytdl_info=None):
    """Patch musicPlayer.Aiogoogle and musicPlayer.YoutubeDL."""

    class _Request:
        def __init__(self, kind):
            self.kind = kind

    class _Resource:
        def __init__(self, kind):
            self._kind = kind

        def list(self, **kwargs):
            return _Request(self._kind)

    class _Youtube:
        search = _Resource("search")
        videos = _Resource("videos")
        playlistItems = _Resource("playlistItems")

    default_meta = {
        "id": search_video_id or "abc123",
        "snippet": {"title": "My Song", "channelTitle": "Test Channel"},
        "contentDetails": {"duration": "PT3M0S"},
    }

    class _FakeAiogoogle:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def discover(self, *args, **kwargs):
            return _Youtube()

        async def as_api_key(self, request):
            if request.kind == "search":
                if search_video_id:
                    return {"items": [{"id": {"videoId": search_video_id}}]}
                return {"items": []}
            if request.kind == "videos":
                return {"items": [video_meta or default_meta]}
            return {"items": []}

    monkeypatch.setattr(musicPlayer, "Aiogoogle", _FakeAiogoogle)

    class _FakeYDL:
        def __init__(self, opts):
            pass

        def extract_info(self, url, download=False):
            return ytdl_info or {"formats": [{"ext": "mp3", "url": "https://stream.example/test.mp3"}]}

    monkeypatch.setattr(musicPlayer, "YoutubeDL", _FakeYDL)
