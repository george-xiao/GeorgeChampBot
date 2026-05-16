from tests import _env_setup  # noqa: F401

import pytest

from tests._capture import CapturedMessages, make_capturing_interaction, assert_snapshot


@pytest.mark.asyncio
async def test_emote_count_existing(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_emote_count_text("kekw")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/count-existing", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_count_missing(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_emote_count_text("nonexistent")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/count-missing", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_leaderboard_page_1(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_leaderboard_text(page=1)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/leaderboard-page-1", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_leaderboard_page_2(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_leaderboard_text(page=2)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/leaderboard-page-2", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_leaderboard_last(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_leaderboard_text(show_last=True)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/leaderboard-last", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_leaderboard_deleted(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_leaderboard_text(show_deleted=True)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/leaderboard-deleted", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_leaderboard_empty_page(seeded_emote_db, guild, regular_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.get_leaderboard_text(page=99)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(regular_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/leaderboard-empty-page", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_transfer_success(seeded_emote_db, guild, admin_member, snapshots_dir):
    from components import emoteLeaderboard
    # oldmeme is deleted (score 80); kekw is active. Transfer should succeed.
    text = await emoteLeaderboard.transfer_emote_score("oldmeme", "kekw")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/transfer-success", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_transfer_failed(seeded_emote_db, guild, admin_member, snapshots_dir):
    from components import emoteLeaderboard
    # kekw is active (not deleted), so transferring FROM kekw should fail.
    text = await emoteLeaderboard.transfer_emote_score("kekw", "pog")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/transfer-failed", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_delete_success(seeded_emote_db, guild, admin_member, snapshots_dir):
    from components import emoteLeaderboard
    # oldmeme is soft-deleted, so admin delete should succeed.
    text = await emoteLeaderboard.delete_emote_entry("oldmeme")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/delete-success", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_delete_active(seeded_emote_db, guild, admin_member, snapshots_dir):
    from components import emoteLeaderboard
    # kekw is active (not soft-deleted), so admin delete should NOT succeed.
    text = await emoteLeaderboard.delete_emote_entry("kekw")

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/delete-active", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_add_score_existing(seeded_emote_db, guild, admin_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.add_emote_score("kekw", 100)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/add-score-existing", snapshots_dir)


@pytest.mark.asyncio
async def test_emote_add_score_missing(seeded_emote_db, guild, admin_member, snapshots_dir):
    from components import emoteLeaderboard
    text = await emoteLeaderboard.add_emote_score("ghostemote", 50)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(admin_member, guild, capture)
    await interaction.response.send_message(text)

    assert_snapshot(capture.to_normalized_list(), "emote/add-score-missing", snapshots_dir)
