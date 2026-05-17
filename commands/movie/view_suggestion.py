import discord
import common.utils as ut
from components.movieNight import SUGGESTION_DATABASE, movie_names_autocomplete


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="view-suggestion", description="View a specific suggestion")
    @discord.app_commands.describe(user="User's movie-suggestion list")
    @discord.app_commands.describe(movie_name="View more details on a specific movie")
    async def view_suggestion(interaction: discord.Interaction, user: discord.Member, movie_name: str):
        if not user:
            user = interaction.user
        reply = SUGGESTION_DATABASE.get_suggestion_embed(user.name, movie_name)
        await interaction.response.send_message(embed=reply)

    view_suggestion.autocomplete("movie_name")(movie_names_autocomplete)
    view_suggestion.error(ut.handle_command_error)
