import discord
from components import memeReview
from common.utils import handle_slash_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="leaderboard", description="Display Meme Review leaderboard")
    @discord.app_commands.describe(page="Page number (default 1)")
    async def leaderboard(interaction: discord.Interaction, page: int = 1):
        text = await memeReview.get_memerboard_text(page, interaction.guild)
        await interaction.response.send_message(text)

    leaderboard.error(handle_slash_command_error)
