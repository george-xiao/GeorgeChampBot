import discord
import common.utils as ut
from .subcomponents.movieNight.movie import Movie
from .subcomponents.movieNight.suggestionDatabase import Suggestions

CONST_SUGGESTION_DB_PATH = './database/movie_suggestion_list.db'
suggestion_database = Suggestions(CONST_SUGGESTION_DB_PATH)
movie_night_group = discord.app_commands.Group(name="movie-night", description="Movie night slash commands")

# add-suggestion command
# Creates a modal that takes movie name, genre and reason for picking as input
# Only allows 10 suggestions to be stored per user
@movie_night_group.command(name="add-suggestion", description="Suggest a movie")
async def add_suggestion(interaction: discord.Interaction):
    if suggestion_database.has_space(interaction.user.name):
        await interaction.response.send_modal(suggestion_modal())
    else:
        reply = discord.Embed(colour= 0x4f4279)
        reply.title="Suggestion List at Capacity!"
        reply.description = "Please remove some suggestions before adding new ones."
        await interaction.response.send_message(embed=reply)

class suggestion_modal(discord.ui.Modal, title = "Suggest a Movie"):
    movie_name = discord.ui.TextInput(label="Movie Name")
    movie_genre = discord.ui.TextInput(label="Movie Genre")
    movie_reason = discord.ui.TextInput(label="Reason for Picking", style = discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.interactions):
        suggested_movie = Movie(self.movie_name.value, self.movie_genre.value, self.movie_reason.value)
        sender = interaction.user.name
        reply = suggestion_database.add_suggestion(sender, suggested_movie)

        await interaction.response.send_message(embed=reply)

# remove-suggestion command
# Removes movie from user's suggestion list
@movie_night_group.command(name='remove-suggestion', description='Remove a previously suggested movie')
@discord.app_commands.describe(movie_name='Name of the movie to be removed from suggestion list')
async def remove_suggestion(interaction: discord.Integration, movie_name: str):
    reply = suggestion_database.remove_suggestion(interaction.user.name, movie_name)
    await interaction.response.send_message(embed=reply)

# list-suggestions command
# Lists all suggestions of a specific user
@movie_night_group.command(name="list-suggestions", description="List all suggestions")
@discord.app_commands.describe(user="User's movie-suggestion list. Defaults to sender")
async def list_suggestions(interaction: discord.Integration, user: discord.Member = None):
    if not user:
        user = interaction.user
    reply = suggestion_database.get_suggestions_embed(user.name)
    await interaction.response.send_message(embed=reply)

# view-suggestion command
# View a specific suggestion of a specific user
@movie_night_group.command(name="view-suggestion", description="View a specific suggestion")
@discord.app_commands.describe(user="User's movie-suggestion list")
@discord.app_commands.describe(movie_name="View more details on specific movie")
async def view_suggestion(interaction: discord.Integration, user: discord.Member, movie_name: str):
    if not user:
        user = interaction.user
    reply = suggestion_database.get_suggestion_embed(user.name, movie_name)
    await interaction.response.send_message(embed=reply)

@remove_suggestion.autocomplete('movie_name')
@view_suggestion.autocomplete('movie_name')
async def movie_names_autocomplete(interaction: discord.Integration, current:str) -> list[discord.app_commands.Choice[str]]:
    if interaction.namespace.user:
        user = ut.get_member(str(interaction.namespace.user.id)).name
    else:
        user = interaction.user.name

    return [
        discord.app_commands.Choice(name=movie_name, value=movie_name)
        for movie_name in suggestion_database.get_suggestion_names(user) if current.lower() in movie_name.lower()
    ]
