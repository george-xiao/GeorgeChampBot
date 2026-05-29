"""Tests for twitch
Commands: /twitch list
          /admin twitch add
          /admin twitch remove

Verifies streamer list display, add/duplicate/invalid handling, and remove paths.
"""

from components import twitchAnnouncement
from tests._dispatch import invoke_slash
from tests._factories import make_member
from tests._stubs import stub_twitch_api


# --- /twitch list ---


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


# --- /admin twitch add ---


async def test_twitch_add_success(db_dir, tree, guild, admin_member, monkeypatch):
    stub_twitch_api(monkeypatch, valid_users=("alicestream",))
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
    stub_twitch_api(monkeypatch, valid_users=())
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
    stub_twitch_api(monkeypatch, valid_users=("alicestream",))
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


# --- /admin twitch remove ---


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
