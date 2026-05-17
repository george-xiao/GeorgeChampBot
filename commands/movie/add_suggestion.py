import discord
import common.utils as ut
from components.movieNight import SUGGESTION_DATABASE
from components.subcomponents.movieNight.movie import Movie


class SuggestionModal(discord.ui.Modal, title="Suggest a Movie"):
    movie_name = discord.ui.TextInput(label="Movie Name")
    movie_genre = discord.ui.TextInput(label="Movie Genre")
    movie_reason = discord.ui.TextInput(label="Reason for Picking", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        suggested_movie = Movie(self.movie_name.value, self.movie_genre.value, self.movie_reason.value)
        sender = interaction.user.name
        reply = SUGGESTION_DATABASE.add_suggestion(sender, suggested_movie)
        await interaction.response.send_message(embed=reply)


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="add-suggestion", description="Suggest a movie using a popup")
    async def add_suggestion(interaction: discord.Interaction):
        await interaction.response.send_modal(SuggestionModal())

    add_suggestion.error(ut.handle_command_error)
