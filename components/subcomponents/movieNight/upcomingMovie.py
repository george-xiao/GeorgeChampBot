import asyncio
from datetime import datetime, timedelta, timezone
import shelve
import discord
from common.asyncTask import AsyncTask
import common.utils as ut
from .movie import Movie
from .suggestionDatabase import Suggestions

# The database stores the following variables:
#   1) upcoming_host_name: str | None
#   2) upcoming_movie: Movie | None
UPCOMING_MOVIE_NIGHT_DB_PATH = "./database/upcoming_movie_night.db"

pickReminderTask: AsyncTask = AsyncTask(lambda: __remind_host_coroutine())
updateEventDescriptionTask = AsyncTask(lambda: __update_movie_event_description(True))


# Allows admins to set upcoming movie night host
# This check has to be done before the function is called
async def set_host(member_name: str) -> discord.Embed:
    # Should only be performed if ScheduledEvent MOVIE_EVENT_NAME exists
    if failed_embed := ut.movie_event_not_present():
        return failed_embed

    event: discord.ScheduledEvent | None = ut.get_movie_event()
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    db["upcoming_host_name"] = member_name
    if db.get("upcoming_movie"):
        del db["upcoming_movie"]
    db.close()

    # Set reminder
    start_pick_reminder()

    # Create and return embedded success-message
    embed = discord.Embed(colour=ut.embed_colour["MOVIE_NIGHT"])
    embed.title = "Movie night host selected!"
    embed.description = f"{ut.get_member_str(member_name)} has been selected as the upcoming movie night host."
    embed.description += f"\nThe movie will be watched on {ut.convert_to_ottawa_time(event.start_time)}."
    await __update_movie_event_description()
    return embed


# Allows admins to reset upcoming movie night host
async def reset_host() -> discord.Embed:
    # Should only be performed if ScheduledEvent MOVIE_EVENT_NAME exists
    if failed_embed := ut.movie_event_not_present():
        return failed_embed

    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    if db.get("upcoming_host_name"):
        del db["upcoming_host_name"]
    if db.get("upcoming_movie"):
        del db["upcoming_movie"]
    db.close()

    # Stop pick reminder for host
    pickReminderTask.stop()

    # Create and return embedded success-message
    embed = discord.Embed(colour=ut.embed_colour["MOVIE_NIGHT"])
    embed.title = "Movie night host reset!"
    embed.description = "Upcoming movie night host has been successfully reset."
    await __update_movie_event_description()
    return embed


# Allows the upcoming movie night host to set the next movie that will be watched
# Validation of member and movie is done here as well
#   member: Only member selected as upcoming_member can select a movie
#   movie:  Only movies from upcoming_member's suggested list can be picked
async def set_movie(member_name: str, movie_name: str, suggestion_database: Suggestions) -> discord.Embed:
    # Should only be performed if ScheduledEvent MOVIE_EVENT_NAME exists
    if failed_embed := ut.movie_event_not_present():
        return failed_embed

    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    upcoming_host_name: str | None = db.get("upcoming_host_name")
    event: discord.ScheduledEvent | None = ut.get_movie_event()

    embed = discord.Embed(colour=ut.embed_colour["ERROR"])
    if not upcoming_host_name:
        embed.title = "You are not the upcoming movie night host!"
        embed.description = "Upcoming movie night host has not been selected yet."
        embed.description += "\nPlease contact a dictator so that they can select a host."
    elif member_name != upcoming_host_name:
        embed.title = "You are not the upcoming movie night host!"
        embed.description = "{upcoming_host_name} is the upcoming movie night host."
        embed.description += "\nPlease contact a dictator if you think there has been a mixup."
    elif not (movie := suggestion_database.get_movie(member_name, movie_name)):
        embed.title = f"{movie_name} does not exist in your suggestion list!"
        embed.description = "Please add the movie to your suggestion list and then try again."
    else:
        db["upcoming_movie"] = movie
        embed.colour = ut.embed_colour["MOVIE_NIGHT"]
        embed.title = f"{member_name} finally picked a movie!"
        embed.description = f"Next movie set as {movie.name}"
        embed.description += f"\nThe movie will be watched on {ut.convert_to_ottawa_time(event.start_time)}."

    db.close()
    await __update_movie_event_description()
    return embed


# Gets more details on the upcoming movie night
# Returns str to be sent as message if successful
# Otherwise, returns an embed that can be sent with a message
def get_upcoming() -> discord.Embed | str:
    # Should only be performed if ScheduledEvent MOVIE_EVENT_NAME exists
    if failed_embed := ut.movie_event_not_present():
        return failed_embed

    return f"[Click here for more details.]({ut.get_movie_event_link()})"


# Sends reminder to upcoming_host every noon until a movie from suggestion-list is picked
def start_pick_reminder():
    if __should_send_reminder():
        pickReminderTask.start()


# Initializes event description whenever the bot restarts
def init_event_description():
    updateEventDescriptionTask.start()


# Event handlers that handles reminder based on how ScheduledEvent is updated
# NOTE: Since a ScheduledEvent's name is not unique, start_event_reminder() is used in every case to ensure consistency
@ut.client.event
async def on_scheduled_event_create(_created_event: discord.ScheduledEvent):
    __update_movie_event_description(updating_description=True)


@ut.client.event
async def on_scheduled_event_update(_old_event: discord.ScheduledEvent, _new_event: discord.ScheduledEvent):
    # The bot updating event description is a false positive
    __update_movie_event_description(updating_description=True)


@ut.client.event
async def on_scheduled_event_delete(_deleted_event: discord.ScheduledEvent):
    __update_movie_event_description(updating_description=True)


# Check to see if host should be reminded to pick a movie for movie night
# Only set up reminders if:
#   1) host has been picked, but not the movie
#   2) ScheduledEvent MOVIE_EVENT_NAME exists
#   3) ScheduledEvent takes place in the future
def __should_send_reminder():
    event: discord.ScheduledEvent | None = ut.get_movie_event()
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    upcoming_host_name: str | None = db.get("upcoming_host_name")
    upcoming_movie: Movie | None = db.get("upcoming_movie")
    db.close()

    return upcoming_host_name and not upcoming_movie and event and datetime.now(timezone.utc) <= event.start_time


# Coroutine to remind the host to pick the movie
# Runs in the background as a task in the following situations:
#   1) every time an upcoming_host has been set
#   2) every time the application restarts
async def __remind_host_coroutine():
    try:
        while True:
            # Set reminder for tomorrow at noon
            next_noon = (datetime.now() + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
            delta = next_noon - datetime.now()
            await asyncio.sleep(delta.total_seconds())

            # Don't send reminders if it is unnecessary
            if not __should_send_reminder():
                return

            # Send reminder since movie has not been picked
            event: discord.ScheduledEvent | None = ut.get_movie_event()
            db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
            upcoming_host_name: str | None = db.get("upcoming_host_name")
            db.close()

            embed = discord.Embed(colour=ut.embed_colour["MOVIE_NIGHT"])
            host_str = ut.get_member_str(upcoming_host_name)
            embed.title = f"{host_str}, please select the upcoming movie!"
            embed.description = f"Please select a movie before {ut.convert_to_ottawa_time(event.start_time)}."
            await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), host_str, embed)
    except Exception as e:
        await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), "Error with Movie Reminder: " + str(e))


# Coroutine to update the description of ScheduledEvent
# Runs in the background as a task in the following situations:
#   1) when a host is picked or reset for the upcoming movie night
#   2) when a host picks a movie for the upcoming movie night
#   3) when the bot restarts
# NOTE: Will only send an edit request if title or description has changed to save on bandwidth
async def __update_movie_event_description(updating_description=False):
    try:
        # Should only be performed if ScheduledEvent MOVIE_EVENT_NAME exists
        if failed_embed := ut.movie_event_not_present(updating_description=updating_description):
            await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), ut.get_role_str("ADMIN_ROLE"), failed_embed)
            return

        event: discord.ScheduledEvent | None = ut.get_movie_event()
        db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
        upcoming_host_name: str | None = db.get("upcoming_host_name")
        upcoming_movie: Movie | None = db.get("upcoming_movie")
        db.close()

        name: str = "Movie Night"
        description: str
        if not upcoming_host_name:
            description = "It's every week bro."
        else:
            name += f" - {upcoming_host_name}"
            if upcoming_movie:
                description = f"**Movie:** {upcoming_movie.name}"
                description += f"\n**Genre:** {upcoming_movie.genre}"
                description += f"\n**Reason for Picking:** {upcoming_movie.picking_reason}"
            else:
                description = "**Movie:** Movie has not been picked yet!"

        # Only send edit request if change is detected
        if event.name != name or event.description != description:
            await event.edit(name=name, description=description)
    except Exception as e:
        await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), "Error with Updating Event: " + str(e))
