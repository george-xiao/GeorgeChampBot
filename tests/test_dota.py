import pytest

from components import dotaReplay
from tests._fixtures import make_member


@pytest.mark.asyncio
async def test_dota_list_populated(seeded_dota_db, snap_send):
    await snap_send(await dotaReplay.get_players_text(), "dota/list-populated")


@pytest.mark.asyncio
async def test_dota_list_empty(db_dir, snap_send):
    await snap_send(await dotaReplay.get_players_text(), "dota/list-empty")


@pytest.mark.asyncio
async def test_dota_add_success(db_dir, snap_send):
    new_member = make_member(103, "carol", nick="Carol")
    await snap_send(await dotaReplay.add_player(new_member, 55555), "dota/add-success")
    assert "carol: 55555" in await dotaReplay.get_players_text()


@pytest.mark.asyncio
async def test_dota_add_duplicate(seeded_dota_db, snap_send):
    alice = make_member(101, "alice")
    # Seeder already has 12345 -> alice; re-adding hits "already exists"
    listing_before = await dotaReplay.get_players_text()
    await snap_send(await dotaReplay.add_player(alice, 12345), "dota/add-duplicate")
    assert await dotaReplay.get_players_text() == listing_before


@pytest.mark.asyncio
async def test_dota_remove_tracked(seeded_dota_db, snap_send):
    # Seeder maps 12345 -> "alice"; autocomplete would pass the player_id key.
    await snap_send(await dotaReplay.remove_player("12345"), "dota/remove-tracked")
    assert "12345" not in await dotaReplay.get_players_text()


@pytest.mark.asyncio
async def test_dota_remove_not_tracked(db_dir, snap_send):
    await snap_send(await dotaReplay.remove_player("99999"), "dota/remove-not-tracked")
