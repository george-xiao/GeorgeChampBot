import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="move", description="Move a queued song to a new position")
    @discord.app_commands.describe(
        move_from="Current 1-indexed position of the song",
        move_to="Target 1-indexed position (default 1)",
    )
    async def move(interaction: discord.Interaction, move_from: int, move_to: int = 1):
        if not await require_voice(interaction):
            return
        text = musicPlayer.move_song(move_from, move_to)
        await interaction.response.send_message(text)

    move.error(handle_slash_command_error)
