import discord
from components import musicPlayer
from common.utils import handle_slash_command_error
from commands.music._helpers import require_voice, send_string_or_embed


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="queue", description="Show the current song queue")
    @discord.app_commands.describe(page="Page number (default 1)")
    async def queue(interaction: discord.Interaction, page: int = 1):
        if not await require_voice(interaction):
            return
        result = musicPlayer.queue_response_page(page)
        await send_string_or_embed(interaction, result)

    queue.error(handle_slash_command_error)
