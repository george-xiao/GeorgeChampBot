import pytest

from components import emoteLeaderboard


@pytest.mark.asyncio
async def test_emote_count_existing(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_emote_count_text("kekw"), "emote/count-existing")


@pytest.mark.asyncio
async def test_emote_count_missing(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_emote_count_text("nonexistent"), "emote/count-missing")


@pytest.mark.asyncio
async def test_emote_leaderboard_page_1(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_leaderboard_text(page=1), "emote/leaderboard-page-1")


@pytest.mark.asyncio
async def test_emote_leaderboard_page_2(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_leaderboard_text(page=2), "emote/leaderboard-page-2")


@pytest.mark.asyncio
async def test_emote_leaderboard_last(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_leaderboard_text(show_last=True), "emote/leaderboard-last")


@pytest.mark.asyncio
async def test_emote_leaderboard_deleted(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_leaderboard_text(show_deleted=True), "emote/leaderboard-deleted")


@pytest.mark.asyncio
async def test_emote_leaderboard_empty_page(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.get_leaderboard_text(page=99), "emote/leaderboard-empty-page")


@pytest.mark.asyncio
async def test_emote_transfer_success(seeded_emote_db, snap_send):
    # oldmeme is deleted (score 80); kekw is active. Transfer succeeds.
    await snap_send(await emoteLeaderboard.transfer_emote_score("oldmeme", "kekw"), "emote/transfer-success")


@pytest.mark.asyncio
async def test_emote_transfer_failed(seeded_emote_db, snap_send):
    # kekw is active (not deleted), so transferring FROM kekw fails.
    await snap_send(await emoteLeaderboard.transfer_emote_score("kekw", "pog"), "emote/transfer-failed")


@pytest.mark.asyncio
async def test_emote_delete_success(seeded_emote_db, snap_send):
    # oldmeme is soft-deleted, so admin delete succeeds.
    await snap_send(await emoteLeaderboard.delete_emote_entry("oldmeme"), "emote/delete-success")


@pytest.mark.asyncio
async def test_emote_delete_active(seeded_emote_db, snap_send):
    # kekw is active (not soft-deleted), so admin delete should NOT succeed.
    await snap_send(await emoteLeaderboard.delete_emote_entry("kekw"), "emote/delete-active")


@pytest.mark.asyncio
async def test_emote_add_score_existing(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.add_emote_score("kekw", 100), "emote/add-score-existing")


@pytest.mark.asyncio
async def test_emote_add_score_missing(seeded_emote_db, snap_send):
    await snap_send(await emoteLeaderboard.add_emote_score("ghostemote", 50), "emote/add-score-missing")
