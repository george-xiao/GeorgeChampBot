"""Integration tests for dota.

Slash commands dispatch through `tree._call`; the periodic task
dispatches through `run_periodic_once` on the same `PeriodicTask`
instance that `dotaReplay.init()` wires up — so a wiring bug in init
(wrong cadence, wrong channel lookup) would fail these tests.

Assertions are on observable behavior (response content, DB state,
captured channel messages), not output snapshots.
"""

from datetime import datetime


import common.utils as ut
from components import dotaReplay
from tests._capture import CapturedMessages, make_capturing_channel
from tests._dispatch import invoke_slash, run_periodic_once
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


# --- Periodic task: hourly OpenDota poll ---


def _recent_match(match_id: int, hero_id: int = 1, won: bool = True) -> dict:
    """Build a minimal OpenDota recentMatches entry timestamped 'now-ish'."""
    now = int(datetime.now().timestamp())
    return {
        "match_id": match_id,
        "start_time": now - 100,
        "duration": 60,
        "game_mode": 1,  # All Pick
        "kills": 10,
        "deaths": 2,
        "assists": 8,
        "xp_per_min": 600,
        "gold_per_min": 500,
        "hero_id": hero_id,
        "radiant_win": True,
        "player_slot": 0 if won else 128,
    }


async def test_dota_recent_matches_reports_recent_game(seeded_dota_db, patched_periodic_start, monkeypatch):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "get_channel", lambda _: channel)

    async def fake_get(url, headers=None):
        if "/12345/recentMatches" in url:
            return [_recent_match(match_id=999001)]
        return []

    monkeypatch.setattr(ut, "async_get_request", fake_get)

    dotaReplay.init()
    await run_periodic_once(dotaReplay._RECENT_MATCHES_TASK)

    contents = [m.content for m in capture.messages]
    embeds = [m for m in capture.messages if m.embed]
    assert any("DotA 2 is still alive" in c for c in contents)
    assert len(embeds) == 1
    assert "999001" in embeds[0].embed["url"]


async def test_dota_recent_matches_silent_when_no_recent_games(seeded_dota_db, patched_periodic_start, monkeypatch):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "get_channel", lambda _: channel)

    async def fake_get(*args, **kwargs):
        return []

    monkeypatch.setattr(ut, "async_get_request", fake_get)

    dotaReplay.init()
    await run_periodic_once(dotaReplay._RECENT_MATCHES_TASK)

    assert capture.messages == []


async def test_dota_recent_matches_handles_api_returning_none(seeded_dota_db, patched_periodic_start, monkeypatch):
    capture = CapturedMessages()
    channel = make_capturing_channel(capture)
    monkeypatch.setattr(ut, "get_channel", lambda _: channel)

    async def fake_get(*args, **kwargs):
        return None

    monkeypatch.setattr(ut, "async_get_request", fake_get)

    dotaReplay.init()
    await run_periodic_once(dotaReplay._RECENT_MATCHES_TASK)

    # API failure per-player → that player is skipped; nothing crashes,
    # nothing is announced.
    assert capture.messages == []
