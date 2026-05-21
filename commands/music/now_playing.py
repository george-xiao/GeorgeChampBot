import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="now-playing", description="Show the currently playing song")
    async def now_playing(interaction: discord.Interaction):
        if not await require_voice(interaction):
            return
        await interaction.response.send_message(embed=musicPlayer.build_now_playing_embed())

    now_playing.error(handle_slash_command_error)
