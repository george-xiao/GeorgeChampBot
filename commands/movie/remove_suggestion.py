import discord
from components.movieNight import SUGGESTION_DATABASE, movie_names_autocomplete, handle_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="remove-suggestion", description="Remove a previously suggested movie")
    @discord.app_commands.describe(movie_name="Name of the movie to be removed from suggestion list")
    async def remove_suggestion(interaction: discord.Interaction, movie_name: str):
        reply = SUGGESTION_DATABASE.remove_suggestion(interaction.user.name, movie_name)
        await interaction.response.send_message(embed=reply)

    remove_suggestion.autocomplete("movie_name")(movie_names_autocomplete)
    remove_suggestion.error(handle_command_error)
