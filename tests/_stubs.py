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


# --- HTTP (aiohttp boundary) ---
#
# Stub aiohttp itself (the library boundary) rather than ut.async_get_request /
# ut.async_post_request (production helpers) — per CLAUDE.md rule #7. This keeps the
# real wrappers in the tested path, including their `status == 200` check.


class _FakeResponse:
    """Stand-in for an aiohttp response: an async context manager with .status + .json()."""

    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return self._payload


class _FakeSession:
    """Stand-in for aiohttp.ClientSession. `router(method, url) -> (json_payload, status)`."""

    def __init__(self, router):
        self._router = router

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def get(self, url, headers=None):
        return _FakeResponse(*self._router("GET", url))

    def post(self, url, data=None):
        return _FakeResponse(*self._router("POST", url))


def stub_aiohttp(monkeypatch, router):
    """Patch aiohttp.ClientSession so ut.async_get_request / ut.async_post_request run
    against fake responses. `router(method, url) -> (json_payload, status)`."""
    monkeypatch.setattr(ut.aiohttp, "ClientSession", lambda: _FakeSession(router))


# --- Dota / OpenDota ---


def stub_dota_api(monkeypatch, *, matches=None, broken=False):
    """Stub the Dota/OpenDota HTTP boundary to return match data (or empty).
    broken=True simulates an API failure (HTTP 500 -> async_get_request returns None)."""

    def router(method, url):
        if broken:
            return None, 500  # non-200 -> wrapper returns None
        if "/recentMatches" in url:
            return (matches if matches is not None else []), 200
        return [], 200

    stub_aiohttp(monkeypatch, router)


# --- Twitch ---


def stub_twitch_api(monkeypatch, *, live_streams=None, valid_users=None, streams_down=False):
    """Stub the Twitch HTTP boundary (valid_users=None accepts any login).
    streams_down=True makes the /streams endpoint fail (HTTP 500 → request returns None)."""
    # Twitch caches OAuth + livestreams at module scope; reset so prior tests don't leak.
    monkeypatch.setattr(twitchAnnouncement, "twitch_OAuth_token", None)
    monkeypatch.setattr(twitchAnnouncement, "twitch_curr_livestreams", {})

    def router(method, url):
        if method == "POST":
            if "id.twitch.tv/oauth2/token" in url:
                return {"access_token": "test-token", "expires_in": 3600}, 200
            return None, 200
        if "id.twitch.tv/oauth2/validate" in url:
            return {"status": 200}, 200
        if "api.twitch.tv/helix/users" in url:
            name = url.rsplit("login=", 1)[-1]
            if valid_users is None or name in valid_users:
                return {"data": [{"login": name, "id": "12345"}]}, 200
            return {"data": []}, 200
        if "api.twitch.tv/helix/streams" in url:
            if streams_down:
                return None, 500
            return {"data": list(live_streams or [])}, 200
        return None, 200

    stub_aiohttp(monkeypatch, router)


# --- YouTube / yt-dlp ---


def stub_youtube(
    monkeypatch,
    *,
    search_video_id=None,
    video_meta=None,
    ytdl_info=None,
    playlist_video_ids=None,
    ytdl_unavailable=False,
):
    """Patch musicPlayer.Aiogoogle and musicPlayer.YoutubeDL.

    playlist_video_ids: ids returned by playlistItems.list (drives the playlist branch).
    ytdl_unavailable=True makes YoutubeDL.extract_info return None (drives the 'unavailable' skip).
    """

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
            if request.kind == "playlistItems":
                # Single page (no nextPageToken) so process_input's pagination loop breaks.
                return {"items": [{"contentDetails": {"videoId": vid}} for vid in (playlist_video_ids or [])]}
            return {"items": []}

    monkeypatch.setattr(musicPlayer, "Aiogoogle", _FakeAiogoogle)

    class _FakeYDL:
        def __init__(self, opts):
            pass

        def extract_info(self, url, download=False):
            if ytdl_unavailable:
                return None
            return ytdl_info or {"formats": [{"ext": "mp3", "url": "https://stream.example/test.mp3"}]}

    monkeypatch.setattr(musicPlayer, "YoutubeDL", _FakeYDL)
