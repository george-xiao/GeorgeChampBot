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

_DEFAULT_CHANNEL_ENV_VARS = ("MEME_CHANNEL", "DOTA_CHANNEL", "MOVIE_CHANNEL")

for _key, _value in _PLACEHOLDERS.items():
    os.environ.setdefault(_key, _value)


# Install a minimal ut.guildObject so module-level imports in code that
# evaluates ut.get_role / ut.get_member at import time (e.g.,
# commands/admin/__init__.py creating the admin Group with default_permissions
# derived from the admin role) succeed before per-test fixtures can fire.
import discord  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402
import common.utils as ut  # noqa: E402


def make_admin_role() -> MagicMock:
    """Build the test admin role. Shared by the bootstrap guild and tests/_factories.py."""
    role = MagicMock()
    role.name = os.environ["ADMIN_ROLE"]
    role.id = 2001
    role.permissions = discord.Permissions(administrator=True)
    return role


def make_movie_role() -> MagicMock:
    """Build the test movie role. Shared by the bootstrap guild and tests/_factories.py."""
    role = MagicMock()
    role.name = os.environ["MOVIE_ROLE"]
    role.id = 2002
    return role


def make_welcome_role() -> MagicMock:
    """Build the test welcome role. Shared by the bootstrap guild and tests/_factories.py."""
    role = MagicMock()
    role.name = os.environ["WELCOME_ROLE"]
    role.id = 2003
    return role


def make_default_channels() -> list:
    """Build named channels for every env-configured channel prod might look up.
    Sending without first calling patch_channel(...) raises — prevents silent swallows."""
    channels = []
    for env_var in _DEFAULT_CHANNEL_ENV_VARS:
        name = os.environ[env_var]
        ch = MagicMock()
        ch.name = name

        async def _refuse(*args, _name=name, **kwargs):
            raise AssertionError(
                f"Test sent to channel '{_name}' without patching. Call patch_channel(monkeypatch, '{_name}')."
            )

        ch.send = _refuse
        channels.append(ch)
    return channels


if ut.guildObject is None:
    _guild = MagicMock()
    _guild.id = 1000
    _guild.name = _PLACEHOLDERS["DISCORD_GUILD"]
    _guild.members = []
    _guild.roles = [make_admin_role(), make_movie_role(), make_welcome_role()]
    _guild.emojis = []
    _guild.channels = make_default_channels()

    ut.guildObject = _guild
