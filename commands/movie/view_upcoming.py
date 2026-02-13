import discord
import common.utils as ut
from components.movieNight import handle_command_error
from components.subcomponents.movieNight import upcomingMovie


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="view-upcoming", description="View more details on upcoming movie night")
    async def view_upcoming(interaction: discord.Interaction):
        result = await upcomingMovie.get_upcoming()
        if isinstance(result, str):
            await interaction.response.send_message(result, delete_after=ut.DEFAULT_MESSAGE_DURATION)
        else:
            await interaction.response.send_message(embed=result)

    view_upcoming.error(handle_command_error)
