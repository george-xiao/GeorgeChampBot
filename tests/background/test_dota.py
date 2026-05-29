"""Background tests for dota — periodic recent-matches check (looptime)."""

import asyncio
from datetime import datetime

import pytest

import common.utils as ut
from components import dotaReplay
from tests._stubs import patch_channel, stub_dota_api

pytestmark = [pytest.mark.looptime]


def _recent_match(match_id: int, hero_id: int = 1, won: bool = True) -> dict:
    now = int(datetime.now().timestamp())
    return {
        "match_id": match_id,
        "start_time": now - 100,
        "duration": 60,
        "game_mode": 1,
        "kills": 10,
        "deaths": 2,
        "assists": 8,
        "xp_per_min": 600,
        "gold_per_min": 500,
        "hero_id": hero_id,
        "radiant_win": True,
        "player_slot": 0 if won else 128,
    }


async def test_dota_recent_matches_reports_recent_game(seeded_dota_db, monkeypatch):
    capture = patch_channel(monkeypatch, ut.env["DOTA_CHANNEL"])
    stub_dota_api(monkeypatch, matches=[_recent_match(match_id=999001)])

    dotaReplay.init()
    await asyncio.sleep(3600)

    contents = [m.content for m in capture.messages]
    embeds = [m for m in capture.messages if m.embed]
    assert any("DotA 2 is still alive" in c for c in contents)
    assert len(embeds) == 1
    assert "999001" in embeds[0].embed["url"]


async def test_dota_recent_matches_silent_when_no_recent_games(seeded_dota_db, monkeypatch):
    capture = patch_channel(monkeypatch, ut.env["DOTA_CHANNEL"])
    stub_dota_api(monkeypatch)  # default: returns [] for /recentMatches

    dotaReplay.init()
    await asyncio.sleep(3600)

    assert capture.messages == []


async def test_dota_recent_matches_handles_api_returning_none(seeded_dota_db, monkeypatch):
    capture = patch_channel(monkeypatch, ut.env["DOTA_CHANNEL"])
    stub_dota_api(monkeypatch, broken=True)  # simulates API failure

    dotaReplay.init()
    await asyncio.sleep(3600)

    assert capture.messages == []
