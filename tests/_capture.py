"""Generic Discord message-capture utilities for slash command snapshot tests.

A slash command response can be plain text, an embed, or (for deferred
commands) multiple messages via followup.send. The shared format normalizes
each invocation to a list of dicts:

    [
        {"content": "Successfully added X", "embed": None},
        {"content": "",                     "embed": {"title": "...", ...}}
    ]

Capture is JSON-serializable so it can be written/read from snapshot files.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord


@dataclass
class SentMessage:
    content: str
    embed: dict | None
    delete_after: float | None = None

    def to_normalized_dict(self) -> dict:
        return {
            "content": _normalize(self.content or ""),
            "embed": _normalize_embed(self.embed) if self.embed else None,
        }


@dataclass
class CapturedMessages:
    messages: list[SentMessage] = field(default_factory=list)

    def to_normalized_list(self) -> list[dict]:
        return [m.to_normalized_dict() for m in self.messages]


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


_MEMBER_MENTION_RE = re.compile(r"<@!?\d+>")
_CHANNEL_MENTION_RE = re.compile(r"<#\d+>")
_ROLE_MENTION_RE = re.compile(r"<@&\d+>")


def _normalize(text: str) -> str:
    text = _MEMBER_MENTION_RE.sub("<@USER>", text)
    text = _CHANNEL_MENTION_RE.sub("<#CHANNEL>", text)
    text = _ROLE_MENTION_RE.sub("<@&ROLE>", text)
    return text


def _normalize_embed(embed_dict: dict) -> dict:
    return json.loads(_normalize(json.dumps(embed_dict, sort_keys=True)))


def load_snapshot(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def write_snapshot(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def assert_snapshot(captured: list[dict], name: str, snapshots_dir: Path) -> None:
    """Compare `captured` against snapshots/<name>.json.

    Run with SNAPSHOT_UPDATE=1 to (re)write the snapshot from `captured`
    instead of asserting. After updating, inspect the JSON and commit
    when correct.
    """
    import os

    path = snapshots_dir / f"{name}.json"
    if os.getenv("SNAPSHOT_UPDATE") or not path.exists():
        write_snapshot(path, captured)
        return
    expected = load_snapshot(path)
    assert captured == expected, (
        f"Snapshot mismatch for {name}. Run SNAPSHOT_UPDATE=1 pytest to refresh "
        f"after verifying the new output is correct."
    )
