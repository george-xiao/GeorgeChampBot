from tests import _env_setup  # noqa: F401

from unittest.mock import AsyncMock, patch

import pytest

from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot
from tests._fixtures import make_member


@pytest.mark.asyncio
async def test_twitch_list_populated(seeded_twitch_db, guild, regular_member, snapshots_dir):
    from components import twitchAnnouncement
    text = await twitchAnnouncement.list_streamers_text()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/list-populated", snapshots_dir)


@pytest.mark.asyncio
async def test_twitch_list_empty(db_dir, guild, regular_member, snapshots_dir):
    from components import twitchAnnouncement
    text = await twitchAnnouncement.list_streamers_text()

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/list-empty", snapshots_dir)


@pytest.mark.asyncio
async def test_twitch_add_success(db_dir, guild, admin_member, snapshots_dir):
    from components import twitchAnnouncement
    alice = make_member(101, "alice")
    with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=True)):
        text = await twitchAnnouncement.add_streamer_to_db(alice, "alicestream")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/add-success", snapshots_dir)


@pytest.mark.asyncio
async def test_twitch_add_invalid_twitch(db_dir, guild, admin_member, snapshots_dir):
    from components import twitchAnnouncement
    alice = make_member(101, "alice")
    with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=False)):
        text = await twitchAnnouncement.add_streamer_to_db(alice, "definitelynotvalid")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/add-invalid-twitch", snapshots_dir)


@pytest.mark.asyncio
async def test_twitch_add_duplicate(seeded_twitch_db, guild, admin_member, snapshots_dir):
    from components import twitchAnnouncement
    alice = make_member(101, "alice")
    # Seed already has alicestream -> alice (id 101); re-add hits "already exists"
    with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=True)):
        text = await twitchAnnouncement.add_streamer_to_db(alice, "alicestream")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/add-duplicate", snapshots_dir)


@pytest.mark.asyncio
async def test_twitch_remove_tracked(seeded_twitch_db, guild, admin_member, snapshots_dir):
    from components import twitchAnnouncement
    text = await twitchAnnouncement.remove_streamer_from_db("alicestream")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/remove-tracked", snapshots_dir)


@pytest.mark.asyncio
async def test_twitch_remove_not_tracked(db_dir, guild, admin_member, snapshots_dir):
    from components import twitchAnnouncement
    text = await twitchAnnouncement.remove_streamer_from_db("ghoststream")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "twitch/remove-not-tracked", snapshots_dir)
