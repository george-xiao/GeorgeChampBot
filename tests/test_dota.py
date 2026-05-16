from tests import _env_setup  # noqa: F401

import pytest

from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot
from tests._fixtures import make_member


@pytest.mark.asyncio
async def test_dota_list_populated(seeded_dota_db, guild, regular_member, snapshots_dir):
    from components import dotaReplay

    text = await dotaReplay.get_players_text()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "dota/list-populated", snapshots_dir)


@pytest.mark.asyncio
async def test_dota_list_empty(db_dir, guild, regular_member, snapshots_dir):
    from components import dotaReplay

    text = await dotaReplay.get_players_text()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "dota/list-empty", snapshots_dir)


@pytest.mark.asyncio
async def test_dota_add_success(db_dir, guild, admin_member, snapshots_dir):
    from components import dotaReplay

    new_member = make_member(103, "carol", nick="Carol")
    text = await dotaReplay.add_player(new_member, 55555)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "dota/add-success", snapshots_dir)


@pytest.mark.asyncio
async def test_dota_add_duplicate(seeded_dota_db, guild, admin_member, snapshots_dir):
    from components import dotaReplay

    alice = make_member(101, "alice")
    # The seeder already has 12345 -> alice (id 101); adding alice/12345 again hits "already exists"
    text = await dotaReplay.add_player(alice, 12345)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "dota/add-duplicate", snapshots_dir)


@pytest.mark.asyncio
async def test_dota_remove_tracked(seeded_dota_db, guild, admin_member, snapshots_dir):
    from components import dotaReplay

    # Seeder maps 12345 -> "alice"; autocomplete would pass the player_id key.
    text = await dotaReplay.remove_player("12345")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "dota/remove-tracked", snapshots_dir)


@pytest.mark.asyncio
async def test_dota_remove_not_tracked(db_dir, guild, admin_member, snapshots_dir):
    from components import dotaReplay

    text = await dotaReplay.remove_player("99999")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "dota/remove-not-tracked", snapshots_dir)
