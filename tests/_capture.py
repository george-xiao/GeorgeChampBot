"""Discord message-capture utilities for slash command integration tests.

A slash command response can be plain text, an embed, or (for deferred
commands) multiple messages via followup.send. `CapturedMessages` collects
each call into a list of `SentMessage` records that tests assert against.
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
    """Return a channel-like mock whose .send() appends to the capture."""

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
    """Mock a discord.Interaction. response.send_message + followup.send both feed `capture`."""

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
