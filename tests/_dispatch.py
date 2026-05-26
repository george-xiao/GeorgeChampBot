"""Slash command dispatch for tests.

Use `invoke_slash(tree, "feature subcommand", user, guild, options={...})`
to trigger a slash command. Returns a `CapturedMessages` with the bot's response.

Supported option types: STRING, INTEGER, BOOLEAN, USER (Member).
"""

from __future__ import annotations

from unittest.mock import MagicMock
from typing import Any

import discord
from discord import app_commands

from tests._capture import CapturedMessages, make_capturing_interaction


_OPTION_TYPE_SUBCOMMAND = 1
_OPTION_TYPE_SUBCOMMAND_GROUP = 2


def _is_member_like(value: Any) -> bool:
    """Check if value is a discord.Member (real or mock)."""
    return isinstance(value, discord.Member)


def _build_leaf_option(name: str, value: Any) -> dict:
    if isinstance(value, bool):
        return {"type": 5, "name": name, "value": value}
    if isinstance(value, int):
        return {"type": 4, "name": name, "value": value}
    if isinstance(value, str):
        return {"type": 3, "name": name, "value": value}
    if _is_member_like(value):
        return {"type": 6, "name": name, "value": str(value.id)}
    raise ValueError(
        f"invoke_slash option {name!r}: unsupported value type {type(value).__name__}. "
        f"Add support in tests/_dispatch.py when needed."
    )


def _build_data(
    command_path: list[str],
    leaf_options: list[dict],
    guild_id: int,
) -> dict:
    """Build the nested `interaction.data` dict for a slash invocation.

    For a single command like ["foo"], options live at the root.
    For ["foo", "bar"], "bar" is a subcommand (type=1).
    For ["foo", "bar", "baz"], "bar" is a subcommand_group (type=2)
    containing "baz" as the subcommand.
    """
    if len(command_path) == 1:
        return {
            "id": 1,
            "name": command_path[0],
            "type": 1,
            "guild_id": str(guild_id),
            "options": leaf_options,
        }

    inner = {
        "type": _OPTION_TYPE_SUBCOMMAND,
        "name": command_path[-1],
        "options": leaf_options,
    }
    for mid in reversed(command_path[1:-1]):
        inner = {
            "type": _OPTION_TYPE_SUBCOMMAND_GROUP,
            "name": mid,
            "options": [inner],
        }
    return {
        "id": 1,
        "name": command_path[0],
        "type": 1,
        "guild_id": str(guild_id),
        "options": [inner],
    }


def _build_member_resolved(options: dict[str, Any] | None, data: dict) -> MagicMock:
    """Wire resolved member data into the payload so discord.py constructs real Members.

    discord.py's Member transformer does isinstance(value, Member) and rejects fakes.
    We feed it raw user/member data via data["resolved"], then intercept state.store_user() to return a mock with the right .name/.id/.bot attributes.
    """
    members_by_id: dict[str, Any] = {}
    for value in (options or {}).values():
        if _is_member_like(value):
            members_by_id[str(value.id)] = value

    state = MagicMock()
    if members_by_id:
        user_data_by_id = {
            uid: {
                "id": uid,
                "username": m.name,
                "discriminator": "0",
                "avatar": None,
                "public_flags": 0,
                "bot": False,
                "global_name": None,
            }
            for uid, m in members_by_id.items()
        }
        data["resolved"] = {
            "users": user_data_by_id,
            "members": {uid: {"user": user_data_by_id[uid], "roles": [], "flags": 0} for uid in members_by_id},
        }

        def _store_user(user_data):
            stub = MagicMock()
            stub.id = int(user_data["id"])
            stub.name = user_data["username"]
            stub.bot = False
            return stub

        state.store_user.side_effect = _store_user

    return state


async def invoke_slash(
    tree: app_commands.CommandTree,
    command_path: str,
    user,
    guild,
    *,
    options: dict[str, Any] | None = None,
) -> CapturedMessages:
    """Trigger a slash command. Returns CapturedMessages with the bot's response.

    `command_path`: space-separated, e.g. "dota list" or "admin dota remove".
    `options`: parameter names → values (types inferred automatically).
    """
    parts = command_path.split()
    if not parts:
        raise ValueError("command_path cannot be empty")

    leaf_options = [_build_leaf_option(n, v) for n, v in (options or {}).items()]
    data = _build_data(parts, leaf_options, guild.id)

    # Build resolved data for any Member-like option values.
    state = _build_member_resolved(options, data)

    capture = CapturedMessages()
    interaction = make_capturing_interaction(user, guild, capture)
    interaction.data = data
    interaction.type = discord.InteractionType.application_command
    interaction.guild_id = guild.id
    interaction.command_failed = False
    interaction._state = state

    await tree._call(interaction)
    return capture
