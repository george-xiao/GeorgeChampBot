import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="pause", description="Toggle pause/resume on the current song")
    async def pause(interaction: discord.Interaction):
        if not await require_voice(interaction):
            return
        text = musicPlayer.toggle_pause()
        await interaction.response.send_message(text)

    pause.error(handle_slash_command_error)
