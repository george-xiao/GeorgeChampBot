"""Shared test data factories.

`make_member` / `make_guild` build the MagicMock entities the integration
tests pass to `invoke_slash`. The `seed_*` functions populate shelve DBs
with deterministic content so each feature's tests have predictable state.
"""

from __future__ import annotations

import shelve
from pathlib import Path
from unittest.mock import MagicMock

import discord


def make_member(member_id: int, name: str, nick: str | None = None, is_admin: bool = False) -> MagicMock:
    # spec=discord.Member so `isinstance(member, discord.Member)` checks
    # in production code (e.g., commands/music/_helpers.py:require_voice)
    # accept the mock. Attribute assignment still works post-spec.
    member = MagicMock(spec=discord.Member)
    member.id = member_id
    member.name = name
    member.display_name = name
    member.nick = nick
    member.bot = False
    member.mention = f"<@{member_id}>"
    member.roles = []
    member.voice = None
    if is_admin:
        admin_role = MagicMock()
        admin_role.name = "ADMIN"
        member.roles.append(admin_role)
    return member


def make_guild(members: list[MagicMock]) -> MagicMock:
    guild = MagicMock()
    guild.id = 1000
    guild.name = "TestGuild"
    guild.members = members
    guild.emojis = []

    by_id = {m.id: m for m in members}

    async def _fetch_member(member_id):
        return by_id.get(int(member_id))

    guild.fetch_member = _fetch_member
    guild.get_member = lambda mid: by_id.get(int(mid))
    return guild


# Fixed cast for deterministic output
DEFAULT_MEMBERS = [
    make_member(101, "alice", nick="Alice the Great"),
    make_member(102, "bob"),
    make_member(103, "carol", nick="Carol"),
    make_member(104, "dave"),
    make_member(105, "eve", nick="Eve", is_admin=True),
]


def seed_meme_leaderboard(db_dir: Path) -> None:
    """Populate database/meme_leaderboard.db with deterministic content."""
    db_path = db_dir / "meme_leaderboard.db"
    with shelve.open(str(db_path)) as s:
        # struct: [memer_score, daily_meme_count]
        s["101"] = [50, 0]
        s["102"] = [30, 0]
        s["103"] = [25, 0]
        s["104"] = [10, 0]
        s["105"] = [5, 0]


def seed_meme_review(db_dir: Path) -> None:
    """Populate database/meme_review.db with deterministic content."""
    db_path = db_dir / "meme_review.db"
    with shelve.open(str(db_path)) as s:
        s["999001"] = [10, True, 101, "https://example.invalid/meme1.png"]


def seed_dota_player_list(db_dir: Path, entries: dict[str, str] | None = None) -> None:
    """Seed the dota DB with {player_id: member_name} entries.

    Defaults: 12345 → alice; 67890 → bob.
    """
    db_path = db_dir / "dota_player_list.db"
    with shelve.open(str(db_path)) as s:
        for k, v in (entries or {"12345": "alice", "67890": "bob"}).items():
            s[k] = v


def seed_emote_leaderboard(db_dir: Path) -> None:
    """Populate the all_time_georgechamp_shelf and starting_date_shelf with deterministic content."""
    from components.emoteLeaderboard import Emoji

    shelf_path = db_dir / "all_time_georgechamp_shelf.db"
    with shelve.open(str(shelf_path)) as s:
        # 12 active emotes with varying scores
        active_data = [
            ("kekw", "<:kekw:101>", 500),
            ("pog", "<:pog:102>", 350),
            ("sadge", "<:sadge:103>", 200),
            ("hype", "<:hype:104>", 175),
            ("cope", "<:cope:105>", 150),
            ("monkas", "<:monkas:106>", 125),
            ("pepega", "<:pepega:107>", 90),
            ("ezclap", "<:ezclap:108>", 70),
            ("widepeepohappy", "<:widepeepohappy:109>", 55),
            ("forsen", "<:forsen:110>", 40),
            ("clap", "<:clap:111>", 25),
            ("five", "<:five:112>", 10),
        ]
        for key, display_name, score in active_data:
            e = Emoji(key, display_name, score)
            s[key] = e

        # 2 deleted emotes
        for key, display_name, score in [("oldmeme", "<:oldmeme:201>", 80), ("retired", "<:retired:202>", 30)]:
            e = Emoji(key, display_name, score)
            e.deleted = True
            s[key] = e

    date_path = db_dir / "starting_date_shelf.db"
    with shelve.open(str(date_path)) as s:
        s["date"] = "01/01/2024"


def seed_movie_suggestions(db_dir: Path) -> None:
    """Populate the movie_suggestion_list shelve with deterministic content."""
    from components.movieNight import SUGGESTION_DATABASE
    from components.subcomponents.movieNight.movie import Movie

    db = SUGGESTION_DATABASE.shelve.open()
    db["alice"] = [
        Movie("Interstellar", "Sci-Fi", "Mind-bending visuals"),
        Movie("Inception", "Sci-Fi", "Dream layers"),
    ]
    db["bob"] = [Movie("Top Gun", "Action", "Maverick")]
    SUGGESTION_DATABASE.shelve.close(modified_dict=db)


def seed_twitch_streamer_list(db_dir: Path, entries: dict[str, str] | None = None) -> None:
    """Seed the twitch DB with {twitch_username: member_name} entries.

    Defaults: alicestream → alice; bobstream → bob.
    """
    db_path = db_dir / "twitch_streamer_list.db"
    with shelve.open(str(db_path)) as s:
        for twitch_username, member_name in (entries or {"alicestream": "alice", "bobstream": "bob"}).items():
            s[twitch_username] = member_name
