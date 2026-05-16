import discord
from components import twitchAnnouncement
from common.utils import handle_slash_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="list", description="List Twitch streamers currently being tracked")
    async def list_twitch(interaction: discord.Interaction):
        text = await twitchAnnouncement.list_streamers_text()
        await interaction.response.send_message(text)

    list_twitch.error(handle_slash_command_error)
