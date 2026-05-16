import discord
import common.utils as ut
from components.subcomponents.movieNight import upcomingMovie, eventReminder
from .subcomponents.movieNight.suggestionDatabase import MovieSuggestions

SUGGESTION_DB_PATH = "./database/movie_suggestion_list.db"
SUGGESTION_DATABASE = MovieSuggestions(SUGGESTION_DB_PATH)


# Code that needs to execute every time the bot starts
def init():
    upcomingMovie.update_event_description(False)
    upcomingMovie.start_pick_reminder()
    eventReminder.start_event_reminder()


# Movie-name autocomplete
# If user field is empty, autocomplete assumes that names should come from requester
async def movie_names_autocomplete(interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    user = interaction.namespace.user
    if user:
        user_id = user.id
        user_name = ut.get_member(str(user_id)).name
    else:
        user_name = interaction.user.name

    return [discord.app_commands.Choice(name=movie_name, value=movie_name) for movie_name in SUGGESTION_DATABASE.get_suggestion_names(user_name) if current.lower() in movie_name.lower()]


# Shared error handler for movie commands
async def handle_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(error)
    if isinstance(error, discord.app_commands.MissingRole):
        await ut.handle_member_not_admin_error(interaction)
    else:
        await ut.handle_slash_command_error(interaction, error)


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
