import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="clear", description="Clear the song queue")
    async def clear(interaction: discord.Interaction):
        if not await require_voice(interaction):
            return
        text = musicPlayer.clear_queue()
        await interaction.response.send_message(text)

    clear.error(handle_slash_command_error)
