"""Fake Discord outputs for test assertions.

Use `make_capturing_interaction(user, guild, capture)` for slash command tests.
Use `make_capturing_channel(capture)` for event handler tests.

Both record sent messages into a `CapturedMessages` instance.
Assert on `capture.messages[0].content` or `.embed`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock

import discord


@dataclass
class SentMessage:
    content: str
    embed: dict | None
    delete_after: float | None = None


@dataclass
class CapturedMessages:
    messages: list[SentMessage] = field(default_factory=list)


def make_capturing_channel(capture: CapturedMessages) -> MagicMock:
    """Fake channel for event handler tests. Patch onto ut.mainChannel or ut.get_channel."""

    async def _send(content="", embed=None, delete_after=None, **kwargs):
        capture.messages.append(
            SentMessage(
                content=content or "",
                embed=embed.to_dict() if isinstance(embed, discord.Embed) else None,
                delete_after=delete_after,
            )
        )
        return MagicMock(id=len(capture.messages))

    channel = MagicMock()
    channel.send = _send
    channel.id = 12345
    return channel


def make_capturing_interaction(user, guild, capture: CapturedMessages) -> MagicMock:
    """Fake interaction for slash command tests. Passed to invoke_slash internally."""

    async def _send_message(content="", embed=None, delete_after=None, **kwargs):
        capture.messages.append(
            SentMessage(
                content=content or "",
                embed=embed.to_dict() if isinstance(embed, discord.Embed) else None,
                delete_after=delete_after,
            )
        )

    async def _followup_send(content="", embed=None, **kwargs):
        capture.messages.append(
            SentMessage(
                content=content or "",
                embed=embed.to_dict() if isinstance(embed, discord.Embed) else None,
            )
        )

    interaction = MagicMock()
    interaction.user = user
    interaction.guild = guild
    interaction.channel = make_capturing_channel(capture)
    interaction.response.send_message = _send_message
    interaction.response.defer = AsyncMock()
    interaction.followup.send = _followup_send
    return interaction
