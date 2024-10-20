import discord
import common.utils as ut
from components.subcomponents.movieNight import upcomingMovie, eventReminder
from .subcomponents.movieNight.movie import Movie
from .subcomponents.movieNight.suggestionDatabase import MovieSuggestions

SUGGESTION_DB_PATH = "./database/movie_suggestion_list.db"
SUGGESTION_DATABASE = MovieSuggestions(SUGGESTION_DB_PATH)
MOVIE_NIGHT_GROUP = discord.app_commands.Group(name="movie", description="Movie night slash commands")


# Code that needs to execute every time the bot starts
def init():
    upcomingMovie.update_event_description(False)
    upcomingMovie.start_pick_reminder()
    eventReminder.start_event_reminder()


# add-suggestion command
# Creates a modal that takes movie name, genre and reason for picking as input
@MOVIE_NIGHT_GROUP.command(name="add-suggestion", description="Suggest a movie using a popup")
async def add_suggestion(interaction: discord.Interaction):
    await interaction.response.send_modal(SuggestionModal())


# add-suggestion modal
class SuggestionModal(discord.ui.Modal, title="Suggest a Movie"):
    movie_name = discord.ui.TextInput(label="Movie Name")
    movie_genre = discord.ui.TextInput(label="Movie Genre")
    movie_reason = discord.ui.TextInput(label="Reason for Picking", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.interactions):
        suggested_movie = Movie(self.movie_name.value, self.movie_genre.value, self.movie_reason.value)
        sender = interaction.user.name
        reply = SUGGESTION_DATABASE.add_suggestion(sender, suggested_movie)

        await interaction.response.send_message(embed=reply)


# remove-suggestion command
# Removes movie from user's suggestion list
@MOVIE_NIGHT_GROUP.command(name="remove-suggestion", description="Remove a previously suggested movie")
@discord.app_commands.describe(movie_name="Name of the movie to be removed from suggestion list")
async def remove_suggestion(interaction: discord.Integration, movie_name: str):
    reply = SUGGESTION_DATABASE.remove_suggestion(interaction.user.name, movie_name)
    await interaction.response.send_message(embed=reply)


# list-suggestions command
# Lists all suggestions of a specific user
@MOVIE_NIGHT_GROUP.command(name="list-suggestions", description="List everyone's suggestions")
async def list_suggestions(interaction: discord.Integration):
    reply = SUGGESTION_DATABASE.get_list_embed()
    await interaction.response.send_message(embed=reply)


# view-suggestion command
# View a specific suggestion of a specific user
@MOVIE_NIGHT_GROUP.command(name="view-suggestion", description="View a specific suggestion")
@discord.app_commands.describe(user="User's movie-suggestion list")
@discord.app_commands.describe(movie_name="View more details on a specific movie")
async def view_suggestion(interaction: discord.Integration, user: discord.Member, movie_name: str):
    if not user:
        user = interaction.user
    reply = SUGGESTION_DATABASE.get_suggestion_embed(user.name, movie_name)
    await interaction.response.send_message(embed=reply)


# pick-host command
# Allows admins to pick the host for upcoming movie night
# User gets reminder to pick movie everyday at noon
@MOVIE_NIGHT_GROUP.command(name="pick-host", description="Pick host for upcoming movie night [Admin Only]")
@discord.app_commands.describe(user="Host for upcoming movie night")
@discord.app_commands.describe(prev_host="Bumps this user to the bottom of the list")
@discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
async def pick_host(interaction: discord.Integration, user: discord.Member, prev_host: discord.Member = None):
    if failed_embed := SUGGESTION_DATABASE.bump_prev_host(prev_host):
        await interaction.response.send_message(ut.get_role_str("ADMIN_ROLE"), embed=failed_embed, delete_after=ut.DEFAULT_MESSAGE_DURATION)
        return
    # Set host has no fail condition, so not validated
    embed = await upcomingMovie.set_host(user.name)
    # If prev_host exists, then bump has to be successful to reach this line
    if prev_host:
        embed.description += f"\n{ut.get_member_str(prev_host.name)} was successfully bumped to the end of the list!"

    await interaction.response.send_message(embed=embed)


# DEPRECATED!; Command not used enough. Removed to reduce bloat
# remove-host command
# Allows admins to reset the host for upcoming movie night
# @MOVIE_NIGHT_GROUP.command(name="remove-host", description="Removes host for upcoming movie night, if any [Admin Only]")
# @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
# async def remove_host(interaction: discord.Integration):
#    embed = await upcomingMovie.remove_host()
#    await interaction.response.send_message(embed=embed)


# pick-movie command
# Allows upcoming host to pick the upcoming movie from suggestion-list
@MOVIE_NIGHT_GROUP.command(name="pick-movie", description="Pick movie for upcoming movie night")
@discord.app_commands.describe(movie_name="Name of the movie from suggested list")
async def pick_movie(interaction: discord.Interaction, movie_name: str):
    embed = await upcomingMovie.set_movie(interaction.user.name, movie_name, SUGGESTION_DATABASE)
    await interaction.response.send_message(embed=embed)


# view-upcoming command
# View more details on the upcoming movie night
@MOVIE_NIGHT_GROUP.command(name="view-upcoming", description="View more details on upcoming movie night")
async def pick_upcoming(interaction: discord.Interaction):
    result = await upcomingMovie.get_upcoming()
    if isinstance(result, str):
        # result is a string if there is an error (Upcoming movie-night is missing)
        await interaction.response.send_message(result, delete_after=ut.DEFAULT_MESSAGE_DURATION)
    else:
        await interaction.response.send_message(embed=result)


# Error handling for movie night commands
@add_suggestion.error
@remove_suggestion.error
@list_suggestions.error
@view_suggestion.error
@pick_host.error
# @remove_host.error
@pick_movie.error
@pick_upcoming.error
async def error_handling(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    # For logging purposes
    print(error)
    if isinstance(error, discord.app_commands.MissingRole):
        await ut.handle_member_not_admin_error(interaction)
    else:
        await ut.handle_slash_command_error(interaction, error)


# Movie-name autocomplete
# If user field is empty, autocomplete assumes that names should come from requester
@remove_suggestion.autocomplete("movie_name")
@view_suggestion.autocomplete("movie_name")
@pick_movie.autocomplete("movie_name")
async def movie_names_autocomplete(interaction: discord.Integration, current: str) -> list[discord.app_commands.Choice[str]]:
    user = interaction.namespace.user
    if user:
        user_id = user.id
        user_name = ut.get_member(str(user_id)).name
    else:
        user_name = interaction.user.name

    return [discord.app_commands.Choice(name=movie_name, value=movie_name) for movie_name in SUGGESTION_DATABASE.get_suggestion_names(user_name) if current.lower() in movie_name.lower()]


# Event handlers that handles reminder based on how ScheduledEvent is updated
# NOTE: Since a ScheduledEvent's name is not unique, update_event_description and start_event_reminder is used in every case to ensure consistency
@ut.client.event
async def on_scheduled_event_create(_created_event: discord.ScheduledEvent):
    upcomingMovie.update_event_description(False)
    eventReminder.start_event_reminder()


@ut.client.event
async def on_scheduled_event_update(old_event: discord.ScheduledEvent, new_event: discord.ScheduledEvent):
    upcomingMovie.update_event_description(False)
    # The bot updating event description is a false positive
    if old_event.start_time == new_event.start_time:
        return
    eventReminder.start_event_reminder()


@ut.client.event
async def on_scheduled_event_delete(_deleted_event: discord.ScheduledEvent):
    upcomingMovie.update_event_description(False)
    eventReminder.start_event_reminder()
