from unittest.mock import AsyncMock, patch

import pytest

from components import twitchAnnouncement
from tests._fixtures import make_member


@pytest.mark.asyncio
async def test_twitch_list_populated(seeded_twitch_db, snap_send):
    await snap_send(await twitchAnnouncement.list_streamers_text(), "twitch/list-populated")


@pytest.mark.asyncio
async def test_twitch_list_empty(db_dir, snap_send):
    await snap_send(await twitchAnnouncement.list_streamers_text(), "twitch/list-empty")


@pytest.mark.asyncio
async def test_twitch_add_success(db_dir, snap_send):
    alice = make_member(101, "alice")
    with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=True)):
        text = await twitchAnnouncement.add_streamer_to_db(alice, "alicestream")
    await snap_send(text, "twitch/add-success")
    assert "alicestream" in await twitchAnnouncement.list_streamers_text()


@pytest.mark.asyncio
async def test_twitch_add_invalid_twitch(db_dir, snap_send):
    alice = make_member(101, "alice")
    with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=False)):
        text = await twitchAnnouncement.add_streamer_to_db(alice, "definitelynotvalid")
    await snap_send(text, "twitch/add-invalid-twitch")
    assert "definitelynotvalid" not in await twitchAnnouncement.list_streamers_text()


@pytest.mark.asyncio
async def test_twitch_add_duplicate(seeded_twitch_db, snap_send):
    alice = make_member(101, "alice")
    # Seed already has alicestream -> alice; re-add hits "already exists"
    listing_before = await twitchAnnouncement.list_streamers_text()
    with patch("components.twitchAnnouncement._validate_twitch_username", new=AsyncMock(return_value=True)):
        text = await twitchAnnouncement.add_streamer_to_db(alice, "alicestream")
    await snap_send(text, "twitch/add-duplicate")
    assert await twitchAnnouncement.list_streamers_text() == listing_before


@pytest.mark.asyncio
async def test_twitch_remove_tracked(seeded_twitch_db, snap_send):
    await snap_send(await twitchAnnouncement.remove_streamer_from_db("alicestream"), "twitch/remove-tracked")
    assert "alicestream" not in await twitchAnnouncement.list_streamers_text()


@pytest.mark.asyncio
async def test_twitch_remove_not_tracked(db_dir, snap_send):
    await snap_send(await twitchAnnouncement.remove_streamer_from_db("ghoststream"), "twitch/remove-not-tracked")
