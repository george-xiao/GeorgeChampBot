"""Integration-test dispatch helpers.

`invoke_slash`: build a fake Interaction payload and feed it to
`CommandTree._call`, exercising the real slash dispatch path
(command lookup, Namespace construction, callback invocation).

`run_periodic_once`: invoke the inner coroutine factory wired into a
`PeriodicTask` exactly once, bypassing the scheduler's sleep loop.

Supports leaf options of type STRING (3), INTEGER (4), BOOLEAN (5),
and USER (6 — Member-like values are auto-resolved). CHANNEL (7) and
ROLE (8) options need extra resolved data; add support when the first
test that needs them lands.
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
    """True for `discord.Member` (real or spec'd MagicMock).
    `make_member` in tests/_fixtures.py builds Member-spec'd mocks."""
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


async def invoke_slash(
    tree: app_commands.CommandTree,
    command_path: str,
    user,
    guild,
    *,
    options: dict[str, Any] | None = None,
) -> CapturedMessages:
    """Dispatch a slash command through `tree._call` with a hand-built Interaction.

    `command_path` is space-separated, e.g. "dota list" or "admin dota remove".
    `options` maps leaf parameter names to Python values; option types are
    inferred from `type(value)`.
    """
    parts = command_path.split()
    if not parts:
        raise ValueError("command_path cannot be empty")

    leaf_options = [_build_leaf_option(n, v) for n, v in (options or {}).items()]
    data = _build_data(parts, leaf_options, guild.id)

    # Build resolved data for any Member-like option values. We use the
    # `resolved.members` path so discord.py constructs a real `discord.Member`
    # — needed because the transformer for a `discord.Member`-annotated param
    # does `isinstance(value, Member)` and rejects anything else.
    #
    # Member.__init__ calls `state.store_user(data['user'])`; we make that
    # return a MagicMock whose .name/.id/.bot match the test's input member,
    # so `member.name` returns the expected string downstream.
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

    capture = CapturedMessages()
    interaction = make_capturing_interaction(user, guild, capture)
    interaction.data = data
    interaction.type = discord.InteractionType.application_command
    interaction.guild_id = guild.id
    interaction.command_failed = False
    interaction._state = state

    await tree._call(interaction)
    return capture


async def run_periodic_once(task) -> None:
    """Invoke a `PeriodicTask`'s inner coroutine factory exactly once.

    Bypasses the scheduler's sleep loop — the schedule math is covered
    separately by `tests/test_periodic_task.py`. This helper exercises
    the actual work-doing coroutine in isolation, so tests can drive
    periodic side effects deterministically.
    """
    await task._coroutine_factory()
