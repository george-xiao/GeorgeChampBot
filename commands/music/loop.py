import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="loop", description="Cycle loop state: queue -> song -> disabled")
    async def loop(interaction: discord.Interaction):
        if not await require_voice(interaction):
            return
        text = musicPlayer.cycle_loop()
        await interaction.response.send_message(text)

    loop.error(handle_slash_command_error)
