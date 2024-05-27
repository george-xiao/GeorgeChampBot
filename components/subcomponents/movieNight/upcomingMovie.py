import asyncio
from datetime import datetime, timedelta
import shelve
import discord
import common.utils as ut
from .movie import Movie
from .suggestionDatabase import Suggestions

# The database stores the following variables:
#   1) upcoming_host_name: str | None
#   2) upcoming_movie: Movie | None
UPCOMING_MOVIE_NIGHT_DB_PATH = "./database/upcoming_movie_night.db"

# Reminder task is a task that runs in the background
# NOTE: Each instance of reminderTask has to be closed before creating a new one
#       This is done with the help of start_reminder()
reminderTask: asyncio.Task | None = None

# Allows admins to set upcoming movie night host
# This check has to be done before the function is called
def set_host(member_name: str, prev_host: discord.User = None) -> discord.Embed:
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    db["upcoming_host_name"] = member_name
    if db.get("upcoming_movie"):
        del db["upcoming_movie"]
    db.close()

    event: discord.ScheduledEvent | None = ut.get_event("Movie Night")
    if not event:
        embed = discord.Embed(colour= ut.embed_colour["ERROR"])
        embed.title = "\"Movie Night\" event does not exist!"
        embed.description = "A Discord Event needs to exist before a host can be picked!"
        embed.description += "Please contact a dictator so that they can create the event."
    else:
        # Set reminder
        start_reminder()

        # Create and return embedded success-message
        embed = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])
        embed.title = "Movie night host selected!"
        embed.description = member_name + " has been selected as the upcoming movie night host."
        embed.description += "\nThe movie will be watched on " + ut.ottawa_time(event.start_time) + "."
        # If prev_host exists, then it is assumed to be successful
        if prev_host:
            embed.description += "\n" + prev_host.name + " was successfully bumped to the end of the list!"
    return embed

# Allows admins to reset upcoming movie night host
def reset_host() -> discord.Embed:
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    if db.get("upcoming_host_name"):
        del db["upcoming_host_name"]
    if db.get("upcoming_movie"):
        del db["upcoming_movie"]
    db.close()

    # Stop reminders
    stop_reminder()

    # Create and return embedded success-message
    embed = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])
    embed.title = "Movie night host reset!"
    embed.description = "Upcoming movie night host has been successfully been reset."
    return embed

# Allows the upcoming movie night host to set the next movie that will be watched
# Validation of member and movie is done here as well
#   member: Only member selected as upcoming_member can select a movie
#   movie:  Only movies from upcoming_member's suggested list can be picked
def set_movie(member_name: str, movie_name: str, suggestion_database: Suggestions) -> discord.Embed:
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    upcoming_host_name: str | None = db.get("upcoming_host_name")
    event: discord.ScheduledEvent | None = ut.get_event("Movie Night")

    embed = discord.Embed(colour= ut.embed_colour["ERROR"])
    if not upcoming_host_name:
        embed.title = "You are not the upcoming movie night host!"
        embed.description = "Upcoming movie night host has not been selected yet."
        embed.description += "Please contact a dictator so that they can select a host."
    elif member_name != upcoming_host_name:
        embed.title = "You are not the upcoming movie night host!"
        embed.description = upcoming_host_name + " is the upcoming movie night host."
        embed.description += "Please contact a dictator if you think there has been a mixup."
    elif not(movie := suggestion_database.get_movie(member_name, movie_name)):
        embed.title = movie_name + " does not exist in your suggestion list!"
        embed.description = "Please add the movie to your suggestion list and then try again."
    else:
        db["upcoming_movie"] = movie
        embed.colour = ut.embed_colour["MOVIE_NIGHT"]
        embed.title = member_name + " finally picked a movie!"
        embed.description = "Next movie set as " + movie.name
        embed.description += "\nThe movie will be watched on " + ut.ottawa_time(event.start_time) + "."

    db.close()
    return embed

# Gets more details on the upcoming movie night
def get_upcoming() -> discord.Embed:
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    upcoming_host_name: str | None = db.get("upcoming_host_name")
    upcoming_movie: Movie | None = db.get("upcoming_movie")
    db.close()

    event: discord.ScheduledEvent | None = ut.get_event("Movie Night")

    embed = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])
    if upcoming_host_name:
        embed.title = upcoming_host_name + "'s Movie Night Detail"
    else:
        embed.colour = ut.embed_colour["ERROR"]
        embed.title = "Host not selected!"
        embed.description = "Please contact a dictator so that they can select a host."
        return embed

    if upcoming_movie:
        embed.description = "**Movie Name:** " + upcoming_movie.name
        embed.description += "\n**Genre:** " + upcoming_movie.genre
        embed.description += "\n**Reason for Picking:** " + upcoming_movie.picking_reason
    else:
        embed.description = "**Movie Name:** Movie has not been picked yet!"
    embed.description += "\n**Time:** " + ut.ottawa_time(event.start_time) + "."

    return embed

# Sends reminder to upcoming_host every noon until a movie from suggestion-list is picked
def start_reminder():
    stop_reminder()

    # Start reminder in the background by creating an event loop
    # Only set up reminders if host has been picked, but not the movie
    db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
    upcoming_host_name: str | None = db.get("upcoming_host_name")
    upcoming_movie: Movie | None = db.get("upcoming_movie")
    db.close()

    if upcoming_host_name and not upcoming_movie:
        global reminderTask
        reminderTask = asyncio.create_task(__remind_host())

# Stop existing reminder (if any exist)
def stop_reminder():
    global reminderTask
    if reminderTask:
        reminderTask.cancel()

# Private reminder function that actually handles reminders
# The function runs as a background task in the following situations:
#   1) every time a upcoming_host has been set
#   2) every time the application restarts
async def __remind_host():
    try:
        while True:
            # Set reminder for tomorrow at noon
            next_noon = (datetime.now() + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
            delta = next_noon - datetime.now()
            await asyncio.sleep(delta.total_seconds())

            db = shelve.open(UPCOMING_MOVIE_NIGHT_DB_PATH)
            upcoming_host_name: str | None = db.get("upcoming_host_name")
            upcoming_movie: Movie | None = db.get("upcoming_movie")
            db.close()

            event: discord.ScheduledEvent | None = ut.get_event("Movie Night")

            # Don't send reminders if host already picked the movie or host has been reset
            if upcoming_movie or not upcoming_host_name:
                break

            # Send reminder since movie has not been picked
            embed = discord.Embed(colour= ut.embed_colour["MOVIE_NIGHT"])
            embed.title = upcoming_host_name + ", please select the upcoming movie!"
            embed.description = "Please select a movie before " + ut.ottawa_time(event.start_time) +"."
            host_id = str(ut.get_member(upcoming_host_name).id)
            await ut.send_message(ut.get_channel(ut.env['MOVIE_CHANNEL']), "<@" + host_id + ">", embedded_msg=embed)
    except Exception as e:
        await ut.send_message(ut.get_channel(ut.env['MOVIE_CHANNEL']), "Error with Movie Reminder: " + str(e))
