"""Tests for dota slash commands (/dota list, /admin dota add, /admin dota remove)."""

from components import dotaReplay
from tests._dispatch import invoke_slash
from tests._factories import make_member


async def test_dota_list_populated(seeded_dota_db, tree, guild, regular_member):
    capture = await invoke_slash(tree, "dota list", regular_member, guild)
    [msg] = capture.messages
    assert "alice: 12345" in msg.content
    assert "bob: 67890" in msg.content


async def test_dota_list_empty(db_dir, tree, guild, regular_member):
    capture = await invoke_slash(tree, "dota list", regular_member, guild)
    [msg] = capture.messages
    assert "empty" in msg.content.lower()


async def test_dota_add_success(db_dir, tree, guild, admin_member):
    new_member = make_member(103, "carol", nick="Carol")
    capture = await invoke_slash(
        tree,
        "admin dota add",
        admin_member,
        guild,
        options={"user": new_member, "player_id": 55555},
    )
    [msg] = capture.messages
    assert "carol" in msg.content
    assert "carol: 55555" in await dotaReplay.get_players_text()


async def test_dota_add_duplicate(seeded_dota_db, tree, guild, admin_member):
    alice = make_member(101, "alice")
    listing_before = await dotaReplay.get_players_text()
    capture = await invoke_slash(
        tree,
        "admin dota add",
        admin_member,
        guild,
        options={"user": alice, "player_id": 12345},
    )
    [msg] = capture.messages
    assert "already exists" in msg.content
    assert await dotaReplay.get_players_text() == listing_before


async def test_dota_remove_tracked(seeded_dota_db, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin dota remove",
        admin_member,
        guild,
        options={"player": "12345"},
    )
    [msg] = capture.messages
    assert "alice" in msg.content
    assert "12345" not in await dotaReplay.get_players_text()


async def test_dota_remove_not_tracked(db_dir, tree, guild, admin_member):
    capture = await invoke_slash(
        tree,
        "admin dota remove",
        admin_member,
        guild,
        options={"player": "99999"},
    )
    [msg] = capture.messages
    assert "99999" in msg.content
    assert "tracked" in msg.content.lower()


async def test_admin_command_denied_for_non_admin(db_dir, tree, guild, regular_member):
    # alice lacks ADMIN → has_role check fails → handle_command_error replies
    new_member = make_member(103, "carol")
    capture = await invoke_slash(
        tree,
        "admin dota add",
        regular_member,
        guild,
        options={"user": new_member, "player_id": 55555},
    )
    [msg] = capture.messages
    assert "admin access is required" in msg.embed["description"].lower()
