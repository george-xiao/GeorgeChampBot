"""Shared helpers for /music slash commands."""

import discord
import common.utils as ut
from components import musicPlayer


async def require_voice(interaction: discord.Interaction) -> bool:
    """Returns True if the user is in a valid voice context; otherwise sends
    an error message and returns False. The caller should early-return on False.
    """
    user = interaction.user
    if not isinstance(user, discord.Member) or user.voice is None or user.voice.channel is None:
        await interaction.response.send_message("Please enter a voice channel")
        return False

    if musicPlayer.vc is not None and ut.botObject is not None:
        bot_voice = getattr(ut.botObject, "voice", None)
        if bot_voice is not None and bot_voice.channel is not None and bot_voice.channel != user.voice.channel:
            await interaction.response.send_message("Please enter the same voice channel as the bot")
            return False

    return True


async def send_string_or_embed(interaction: discord.Interaction, result):
    """Sends either a plain-text result or a Discord embed result via the slash response."""
    if isinstance(result, discord.Embed):
        await interaction.response.send_message(embed=result)
    else:
        await interaction.response.send_message(result)
