import discord
from components import dotaReplay
from common.utils import handle_slash_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="list", description="List Dota players currently being tracked")
    async def list(interaction: discord.Interaction):
        text = await dotaReplay.get_players_text()
        await interaction.response.send_message(text)

    list.error(handle_slash_command_error)
