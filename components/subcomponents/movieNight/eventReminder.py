import asyncio
from datetime import datetime, timedelta, timezone
import pickle
import discord
from common.asyncTask import AsyncTask
import common.utils as ut

REMINDER_THRESHOLD = 1 * 60 * 60
eventReminderTask: AsyncTask | None = AsyncTask(lambda: __remind_event_coroutine())
LAST_EVENT_PATH = "./database/last_event_start_time.pkl"


# Sends reminder to everyone with MOVIE_ROLE REMINDER_THRESHOLD before the event starts
def start_event_reminder():
    eventReminderTask.start()


# Check to see if everyone with MOVIE_ROLE needs to be reminded about the event
# Only set up reminders if:
#   1) event exists
#   2) event is scheduled
#   3) event occurs in the future
#   4) a reminder was not already sent for this event
async def __should_send_remind() -> bool:
    event: discord.ScheduledEvent | None = await ut.get_movie_event()
    if not event:
        return False

    is_event_sent: bool = False
    try:
        with open(LAST_EVENT_PATH, "rb") as file:
            last_event_start_time = pickle.load(file)
            is_event_sent = isinstance(last_event_start_time, datetime) and last_event_start_time == event.start_time
    except FileNotFoundError:
        is_event_sent = False

    return not is_event_sent and event.status is discord.EventStatus.scheduled and datetime.now(timezone.utc) <= event.start_time


# Coroutine to remind everyone with MOVIE_ROLE REMINDER_THRESHOLD before the event starts
# Runs in the background task in the following situations:
#   1) every time the ScheduledEvent MOVIE_EVENT_NAME changes
#   2) every time the application restarts
async def __remind_event_coroutine():
    if await __should_send_remind():
        try:
            event: discord.ScheduledEvent | None = await ut.get_movie_event()
            # Set reminder for REMINDER_THRESHOLD before event starts
            reminder_threshold = event.start_time - timedelta(seconds=REMINDER_THRESHOLD)
            delta = reminder_threshold - datetime.now(timezone.utc)
            await asyncio.sleep(delta.total_seconds())

            # Ensure that currently it is REMINDER_THRESHOLD before the event is supposed to start.
            reminder_threshold = event.start_time - timedelta(seconds=REMINDER_THRESHOLD)
            now = datetime.now(timezone.utc)
            if not reminder_threshold <= now <= event.start_time:
                print("Skipping an event reminder")
                return

            # Send reminder since movie starts within REMINDER_THRESHOLD
            event_link = await ut.get_movie_event_link()
            movie_role = ut.get_role_str("MOVIE_ROLE")
            event_description = f"Movie night alert! [Get your popcorn ready!]({event_link}) 🍿"
            await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), f"{movie_role} {event_description}", delete_after=ut.EXTENDED_MESSAGE_DURATION)

            with open(LAST_EVENT_PATH, "wb") as file:
                pickle.dump(event.start_time, file)
        except Exception as e:
            await ut.send_message(ut.get_channel(ut.env["MOVIE_CHANNEL"]), "Error with Event Reminder: " + str(e))
