import discord
from components.movieNight import SUGGESTION_DATABASE, movie_names_autocomplete, handle_command_error
from components.subcomponents.movieNight import upcomingMovie


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="pick-movie", description="Pick movie for upcoming movie night")
    @discord.app_commands.describe(movie_name="Name of the movie from suggested list")
    async def pick_movie(interaction: discord.Interaction, movie_name: str):
        embed = await upcomingMovie.set_movie(interaction.user.name, movie_name, SUGGESTION_DATABASE)
        await interaction.response.send_message(embed=embed)

    pick_movie.autocomplete("movie_name")(movie_names_autocomplete)
    pick_movie.error(handle_command_error)
