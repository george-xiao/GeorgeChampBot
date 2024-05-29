import asyncio
from datetime import datetime, timedelta, timezone
import discord
from common.asyncTask import AsyncTask
import common.utils as ut

REMINDER_THRESHOLD_SECONDS = 1 * 60 * 60
eventReminderTask: AsyncTask | None = AsyncTask(lambda: __remind_event_coroutine())


# Sends reminder to everyone with MOVIE_ROLE REMINDER_THRESHOLD_SECONDS before the event starts
# Only set up reminders if:
#   1) event has been created
#   2) event is not live
#   2) event occurs in the future
def start_event_reminder():
    event: discord.ScheduledEvent | None = ut.get_event("Movie Night")
    if event and event.status is not discord.EventStatus.active and datetime.now(timezone.utc) <= event.start_time:
        eventReminderTask.start()


# Event handlers that handles reminder based on how ScheduledEvent is updated
# NOTE: Since a ScheduledEvent's name is not unique, start_event_reminder() is used in every case to ensure consistency
@ut.client.event
async def on_scheduled_event_create(_created_event: discord.ScheduledEvent):
    start_event_reminder()


@ut.client.event
async def on_scheduled_event_update(_old_event: discord.ScheduledEvent, _new_event: discord.ScheduledEvent):
    start_event_reminder()


@ut.client.event
async def on_scheduled_event_delete(_deleted_event: discord.ScheduledEvent):
    start_event_reminder()


# Coroutine to remind everyone with MOVIE_ROLE REMINDER_THRESHOLD_SECONDS before the event starts
# Runs in the background task in the following situations:
#   1) every time the ScheduledEvent "Movie Night" changes
#   2) every time the application restarts
async def __remind_event_coroutine():
    try:
        # Set reminder for REMINDER_THRESHOLD_SECONDS before event starts
        event: discord.ScheduledEvent = ut.get_event("Movie Night")
        reminder_threshold = event.start_time - timedelta(seconds=REMINDER_THRESHOLD_SECONDS)
        delta = reminder_threshold - datetime.now(timezone.utc)
        await asyncio.sleep(delta.total_seconds())

        # Ensure that currently it is REMINDER_THRESHOLD_SECONDS before the event is supposed to start.
        reminder_threshold = event.start_time - timedelta(seconds=REMINDER_THRESHOLD_SECONDS)
        now = datetime.now(timezone.utc)
        if not (reminder_threshold <= now <= event.start_time):
            return

        # Send reminder since movie starts within REMINDER_THRESHOLD_SECONDS
        embed = discord.Embed(colour=ut.embed_colour["MOVIE_NIGHT"])
        embed.title = "Movie night alert!"
        time_format = str(event.start_time - now).split(".", maxsplit=1)[0]
        embed.description = "T-minus " + time_format + " until movie night starts!"
        embed.description += "\nGet your popcorn ready! 🍿"
        movie_role = ut.get_role(ut.env["MOVIE_ROLE"])
        await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), "<@&" + str(movie_role.id) + "> ", embedded_msg=embed)
    except Exception as e:
        await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), "Error with Event Reminder: " + str(e))
