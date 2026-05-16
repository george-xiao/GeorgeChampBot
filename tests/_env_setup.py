"""Set placeholder env vars before common.utils is imported.

common/utils.py reads env at import time and casts ANNOUNCEMENT_* to int,
so missing values crash imports. Importing this module FIRST in any
test/conftest/snapshot file ensures common.utils can be imported safely.

load_dotenv() defaults to override=False, so any values set here win over
whatever the real .env contains.
"""

import os

_PLACEHOLDERS = {
    "DISCORD_TOKEN": "test-token",
    "DISCORD_GUILD": "TestGuild",
    "BOT_ID": "999",
    "ADMIN_ROLE": "ADMIN",
    "MAIN_CHANNEL": "general",
    "BOT_CHANNEL": "bot",
    "ANNOUNCEMENT_CHANNEL": "announcements",
    "ANNOUNCEMENT_DAY": "0",
    "ANNOUNCEMENT_HOUR": "12",
    "ANNOUNCEMENT_MIN": "0",
    "WELCOME_ROLE": "WELCOME",
    "DOTA_CHANNEL": "dota",
    "TWITCH_CLIENT_ID": "test-twitch-client-id",
    "TWITCH_CLIENT_SECRET": "test-twitch-client-secret",
    "MEME_CHANNEL": "memes",
    "YOUTUBE_API_KEY": "test-youtube-api-key",
    "MOVIE_CHANNEL": "movie-night",
    "MOVIE_ROLE": "MOVIE",
}

for _key, _value in _PLACEHOLDERS.items():
    os.environ.setdefault(_key, _value)


# Install a minimal ut.guildObject so module-level imports in code that
# evaluates ut.get_role / ut.get_member at import time (e.g.,
# commands/admin/__init__.py creating the admin Group with default_permissions
# derived from the admin role) succeed before per-test fixtures can fire.
import discord  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402
import common.utils as ut  # noqa: E402

if ut.guildObject is None:
    _admin_role = MagicMock()
    _admin_role.name = _PLACEHOLDERS["ADMIN_ROLE"]
    _admin_role.id = 2001
    _admin_role.permissions = discord.Permissions(administrator=True)

    _guild = MagicMock()
    _guild.id = 1000
    _guild.name = _PLACEHOLDERS["DISCORD_GUILD"]
    _guild.members = []
    _guild.roles = [_admin_role]
    _guild.emojis = []

    ut.guildObject = _guild
