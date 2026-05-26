"""External API stubs. Call with monkeypatch to fake network dependencies.

Use `stub_dota_api(monkeypatch, matches=[...])` for Dota/OpenDota.
Use `stub_twitch_api(monkeypatch, live_streams=[...])` for Twitch.
Use `stub_youtube(monkeypatch, search_video_id="...")` for YouTube/yt-dlp.
"""

import common.utils as ut
from components import musicPlayer


def stub_dota_api(monkeypatch, *, matches=None):
    """Patch ut.async_get_request to return Dota match data (or empty)."""

    async def fake_get(url, headers=None):
        if "/recentMatches" in url:
            return matches if matches is not None else []
        return []

    monkeypatch.setattr(ut, "async_get_request", fake_get)


def stub_twitch_api(monkeypatch, *, live_streams=None):
    """Patch ut.async_get_request and ut.async_post_request to mimic Twitch."""

    async def fake_get(url, headers=None):
        if "id.twitch.tv/oauth2/validate" in url:
            return {"status": 200}
        if "api.twitch.tv/helix/users" in url:
            name = url.rsplit("login=", 1)[-1]
            return {"data": [{"login": name, "id": "12345"}]}
        if "api.twitch.tv/helix/streams" in url:
            return {"data": list(live_streams or [])}
        return None

    async def fake_post(url, body):
        if "id.twitch.tv/oauth2/token" in url:
            return {"access_token": "test-token", "expires_in": 3600}
        return None

    monkeypatch.setattr(ut, "async_get_request", fake_get)
    monkeypatch.setattr(ut, "async_post_request", fake_post)


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
