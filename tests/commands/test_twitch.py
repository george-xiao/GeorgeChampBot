"""Tests for twitch slash commands (/twitch list, /admin twitch add, /admin twitch remove)."""

import pytest

import common.utils as ut
from components import twitchAnnouncement
from tests._dispatch import invoke_slash
from tests._factories import make_member


# --- Twitch HTTP stub helpers ---


def _stub_twitch(monkeypatch, *, valid_users=(), live_streams=(), validate_ok=True):
    """Stub ut.async_get_request and ut.async_post_request to mimic Twitch.

    valid_users: usernames the Helix /users endpoint should report as existing.
    live_streams: list of dicts {"user_name": str, "viewer_count": int} the
        Helix /streams endpoint should report as live.
    validate_ok: whether /oauth2/validate should report a healthy token.
    """

    async def fake_get(url, headers=None):
        if "id.twitch.tv/oauth2/validate" in url:
            return {"status": 200} if validate_ok else {"status": 401}
        if "api.twitch.tv/helix/users" in url:
            name = url.rsplit("login=", 1)[-1]
            if name in valid_users:
                return {"data": [{"login": name, "id": "12345"}]}
            return {"data": []}
        if "api.twitch.tv/helix/streams" in url:
            return {"data": list(live_streams)}
        return None

    async def fake_post(url, body):
        if "id.twitch.tv/oauth2/token" in url:
            return {"access_token": "test-token", "expires_in": 3600}
        return None

    monkeypatch.setattr(ut, "async_get_request", fake_get)
    monkeypatch.setattr(ut, "async_post_request", fake_post)


@pytest.fixture(autouse=True)
def reset_twitch_module_state():
    """Twitch module caches OAuth + livestreams at module scope; clear between tests."""
    twitchAnnouncement.twitch_OAuth_token = None
    twitchAnnouncement.twitch_curr_livestreams = {}
    yield
    twitchAnnouncement.twitch_OAuth_token = None
    twitchAnnouncement.twitch_curr_livestreams = {}


# --- Slash commands ---


async def test_twitch_list_populated(seeded_twitch_db, tree, guild, regular_member):
    capture = await invoke_slash(tree, "twitch list", regular_member, guild)
    [msg] = capture.messages
    assert "alice" in msg.content
    assert "alicestream" in msg.content
    assert "bobstream" in msg.content


async def test_twitch_list_empty(db_dir, tree, guild, regular_member):
    capture = await invoke_slash(tree, "twitch list", regular_member, guild)
    [msg] = capture.messages
    assert "not tracking" in msg.content.lower()


async def test_twitch_add_success(db_dir, tree, guild, admin_member, monkeypatch):
    _stub_twitch(monkeypatch, valid_users=("alicestream",))
    alice = make_member(101, "alice")
    capture = await invoke_slash(
        tree,
        "admin twitch add",
        admin_member,
        guild,
        options={"user": alice, "twitch_username": "alicestream"},
    )
    [msg] = capture.messages
    assert "alice" in msg.content
    assert "alicestream" in await twitchAnnouncement.list_streamers_text()


async def test_twitch_add_invalid_twitch(db_dir, tree, guild, admin_member, monkeypatch):
    _stub_twitch(monkeypatch, valid_users=())
    alice = make_member(101, "alice")
    capture = await invoke_slash(
        tree,
        "admin twitch add",
        admin_member,
        guild,
        options={"user": alice, "twitch_username": "definitelynotvalid"},
    )
    [msg] = capture.messages
    assert "not a valid" in msg.content.lower()
    assert "definitelynotvalid" not in await twitchAnnouncement.list_streamers_text()


async def test_twitch_add_duplicate(seeded_twitch_db, tree, guild, admin_member, monkeypatch):
    _stub_twitch(monkeypatch, valid_users=("alicestream",))
    alice = make_member(101, "alice")
    listing_before = await twitchAnnouncement.list_streamers_text()
    capture = await invoke_slash(
        tree,
        "admin twitch add",
        admin_member,
        guild,
        options={"user": alice, "twitch_username": "alicestream"},
    )
    [msg] = capture.messages
    assert "already exists" in msg.content.lower()
    assert await twitchAnnouncement.list_streamers_text() == listing_before


async def test_twitch_remove_tracked(seeded_twitch_db, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin twitch remove",
        admin_member,
        guild,
        options={"streamer": "alicestream"},
    )
    [msg] = capture.messages
    assert "alice" in msg.content
    assert "alicestream" not in await twitchAnnouncement.list_streamers_text()


async def test_twitch_remove_not_tracked(db_dir, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin twitch remove",
        admin_member,
        guild,
        options={"streamer": "ghoststream"},
    )
    [msg] = capture.messages
    assert "isn't being tracked" in msg.content
