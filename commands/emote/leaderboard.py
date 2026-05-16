import discord
from components import emoteLeaderboard
from common.utils import handle_slash_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="leaderboard", description="Show the all-time emote leaderboard")
    @discord.app_commands.describe(
        page="Page number (default 1)",
        show_last="Show the last page (overrides page)",
        show_deleted="Show deleted emotes instead of active ones",
    )
    async def leaderboard(interaction: discord.Interaction, page: int = 1, show_last: bool = False, show_deleted: bool = False):
        text = await emoteLeaderboard.get_leaderboard_text(page=page, show_last=show_last, show_deleted=show_deleted)
        await interaction.response.send_message(text)

    leaderboard.error(handle_slash_command_error)
