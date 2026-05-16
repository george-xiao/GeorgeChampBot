import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="disconnect", description="Disconnect the bot from voice")
    async def disconnect(interaction: discord.Interaction):
        if not await require_voice(interaction):
            return
        text = await musicPlayer.disconnect_voice()
        await interaction.response.send_message(text)

    disconnect.error(handle_slash_command_error)
