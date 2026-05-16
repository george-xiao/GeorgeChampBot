import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="play", description="Play a YouTube song or playlist")
    @discord.app_commands.describe(query="YouTube URL or search terms")
    async def play(interaction: discord.Interaction, query: str):
        if not await require_voice(interaction):
            return
        await interaction.response.defer()
        messages = await musicPlayer.play_song_request(interaction.user, interaction.user.voice.channel, query)
        for msg in messages:
            await interaction.followup.send(msg)

    play.error(handle_slash_command_error)
