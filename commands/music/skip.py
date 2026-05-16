import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="skip", description="Skip the current song or a queued one")
    @discord.app_commands.describe(song_num="Queue position (1-indexed) to skip. Omit to skip current.")
    async def skip(interaction: discord.Interaction, song_num: int = 0):
        if not await require_voice(interaction):
            return
        text = musicPlayer.skip_song(song_num)
        await interaction.response.send_message(text)

    skip.error(handle_slash_command_error)
