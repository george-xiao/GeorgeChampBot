import discord
import common.utils as ut
import components.subcomponents.movieNight.upcomingMovie as upcomingMovie
from .subcomponents.movieNight.movie import Movie
from .subcomponents.movieNight.suggestionDatabase import Suggestions

CONST_SUGGESTION_DB_PATH = "./database/movie_suggestion_list.db"
suggestion_database = Suggestions(CONST_SUGGESTION_DB_PATH)
movie_night_group = discord.app_commands.Group(name="movie", description="Movie night slash commands")

# Code that needs to execute every time the bot starts
def init():
    upcomingMovie.start_reminder()

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

# add-suggestion modal
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
@movie_night_group.command(name="remove-suggestion", description="Remove a previously suggested movie")
@discord.app_commands.describe(movie_name="Name of the movie to be removed from suggestion list")
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
@discord.app_commands.describe(movie_name="View more details on a specific movie")
async def view_suggestion(interaction: discord.Integration, user: discord.Member, movie_name: str):
    if not user:
        user = interaction.user
    reply = suggestion_database.get_suggestion_embed(user.name, movie_name)
    await interaction.response.send_message(embed=reply)

# pick-host command
# Allows admins to pick the host for upcoming movie night
# User gets reminder to pick movie everyday at noon
@movie_night_group.command(name="pick-host", description="Pick host for upcoming movie night [Admin Only]")
@discord.app_commands.describe(user="Host for upcoming movie night")
@discord.app_commands.describe(time="Start time for upcoming movie night")
@discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
async def pick_host(interaction: discord.Integration, user: discord.Member, time: str):
    embed = upcomingMovie.set_host(user.name, time)
    await interaction.response.send_message(embed=embed)

# reset-host command
# Allows admins to reset the host for upcoming movie night
@movie_night_group.command(name="reset-host", description="Resets host for upcoming movie night, if any [Admin Only]")
@discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
async def reset_host(interaction: discord.Integration):
    embed = upcomingMovie.reset_host()
    await interaction.response.send_message(embed=embed)

# pick-movie command
# Allows upcoming host to pick the upcoming movie from suggestion-list
@movie_night_group.command(name="pick-movie", description="Pick movie for upcoming movie night")
@discord.app_commands.describe(movie_name="Name of the movie from suggested list")
async def pick_movie(interaction: discord.Interaction, movie_name: str):
    embed = upcomingMovie.set_movie(interaction.user.name, movie_name, suggestion_database)
    await interaction.response.send_message(embed=embed)

# view-upcoming command
# View more details on the upcoming movie night
@movie_night_group.command(name="view-upcoming", description="View more details on upcoming movie night")
async def pick_upcoming(interaction: discord.Interaction):
    embed = upcomingMovie.get_upcoming()
    await interaction.response.send_message(embed=embed)

# Member not admin error
@pick_host.error
@reset_host.error
async def member_not_admin_error(interaction: discord.Interaction, error):
    print(error)
    await ut.member_not_admin_error(interaction)

# Movie-name autocomplete
# If user field is empty, autocomplete assumes that names should come from requester
@remove_suggestion.autocomplete("movie_name")
@view_suggestion.autocomplete("movie_name")
@pick_movie.autocomplete("movie_name")
async def movie_names_autocomplete(interaction: discord.Integration, current:str) -> list[discord.app_commands.Choice[str]]:
    if interaction.namespace.user:
        user = ut.get_member(str(interaction.namespace.user.id)).name
    else:
        user = interaction.user.name

    return [
        discord.app_commands.Choice(name=movie_name, value=movie_name)
        for movie_name in suggestion_database.get_suggestion_names(user) if current.lower() in movie_name.lower()
    ]
