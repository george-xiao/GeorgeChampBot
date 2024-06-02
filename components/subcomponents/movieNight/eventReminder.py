import asyncio
from datetime import datetime, timedelta, timezone
import pickle
import discord
from common.asyncTask import AsyncTask
import common.utils as ut

REMINDER_THRESHOLD_SECONDS = 1 * 60 * 60
eventReminderTask: AsyncTask | None = AsyncTask(lambda: __remind_event_coroutine())
LAST_EVENT_PATH= "./database/last_event_start_time.pkl"


# Sends reminder to everyone with MOVIE_ROLE REMINDER_THRESHOLD_SECONDS before the event starts
# Only set up reminders if:
#   1) event has been created
#   2) event is scheduled
#   3) event occurs in the future
#   4) a reminder was not already sent for this event
def start_event_reminder():
    event: discord.ScheduledEvent | None = ut.get_movie_event()
    is_event_sent: bool
    try:
        with open(LAST_EVENT_PATH, 'rb') as file:
            last_event_start_time = pickle.load(file)
            is_event_sent = isinstance(last_event_start_time, datetime) and last_event_start_time == event.start_time
    except FileNotFoundError:
        is_event_sent = False
    if event.status is discord.EventStatus.scheduled and datetime.now(timezone.utc) <= event.start_time and not is_event_sent:
        eventReminderTask.start()


# Event handlers that handles reminder based on how ScheduledEvent is updated
# NOTE: Since a ScheduledEvent's name is not unique, start_event_reminder() is used in every case to ensure consistency
@ut.client.event
async def on_scheduled_event_create(_created_event: discord.ScheduledEvent):
    start_event_reminder()


@ut.client.event
async def on_scheduled_event_update(old_event: discord.ScheduledEvent, new_event: discord.ScheduledEvent):
    # The bot updating event description is a false positive
    if old_event.start_time == new_event.start_time:
        return
    start_event_reminder()


@ut.client.event
async def on_scheduled_event_delete(_deleted_event: discord.ScheduledEvent):
    start_event_reminder()


# Coroutine to remind everyone with MOVIE_ROLE REMINDER_THRESHOLD_SECONDS before the event starts
# Runs in the background task in the following situations:
#   1) every time the ScheduledEvent MOVIE_EVENT_NAME changes
#   2) every time the application restarts
async def __remind_event_coroutine():
    try:
        # Set reminder for REMINDER_THRESHOLD_SECONDS before event starts
        event: discord.ScheduledEvent = ut.get_movie_event()
        reminder_threshold = event.start_time - timedelta(seconds=REMINDER_THRESHOLD_SECONDS)
        delta = reminder_threshold - datetime.now(timezone.utc)
        await asyncio.sleep(delta.total_seconds())

        # Ensure that currently it is REMINDER_THRESHOLD_SECONDS before the event is supposed to start.
        reminder_threshold = event.start_time - timedelta(seconds=REMINDER_THRESHOLD_SECONDS)
        now = datetime.now(timezone.utc)
        if not reminder_threshold <= now <= event.start_time:
            return

        # Send reminder since movie starts within REMINDER_THRESHOLD_SECONDS
        event_link = ut.get_movie_event_link()
        movie_role = ut.get_role_str("MOVIE_ROLE")
        event_description = f"Movie night alert! [Get your popcorn ready!]({event_link}) 🍿"
        await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), f"{movie_role} {event_description}", delete_after=ut.DELETE_AFTER_HOURS)

        with open(LAST_EVENT_PATH, 'wb') as file:
            pickle.dump(event.start_time, file)
    except Exception as e:
        await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), "Error with Event Reminder: " + str(e))
