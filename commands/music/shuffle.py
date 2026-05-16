import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="shuffle", description="Shuffle the queue")
    async def shuffle(interaction: discord.Interaction):
        if not await require_voice(interaction):
            return
        text = musicPlayer.shuffle_queue()
        await interaction.response.send_message(text)

    shuffle.error(handle_slash_command_error)
