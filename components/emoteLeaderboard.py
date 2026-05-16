import math
import shelve
import re
from collections import Counter
from datetime import date
import discord
import common.utils as ut
from common.periodicTask import PeriodicTask

WEEKLY_EMOTE_LIMIT = 250
_ANNOUNCEMENT_TASK = None


def init():
    """Start the periodic emote-leaderboard announcement task."""
    global _ANNOUNCEMENT_TASK
    _ANNOUNCEMENT_TASK = PeriodicTask.weekly(
        ut.env["ANNOUNCEMENT_DAY"],
        ut.env["ANNOUNCEMENT_HOUR"],
        ut.env["ANNOUNCEMENT_MIN"],
        announcement_task,
    )
    _ANNOUNCEMENT_TASK.start()


class Emoji:
    def __init__(self, key, display_name, score=0):
        self.key = key
        self.display_name = display_name
        self.score = score
        self.w_score = 0
        self.deleted = False

    def update_emote(self, display_name):
        self.display_name = display_name
        self.deleted = False

    def award(self, score):
        self.score += score
        self.w_score += score


# Converts either formats: <EmoteName:123> or EmoteName
def dname_to_key(display_name):
    if display_name.count(":") == 2:
        return display_name.split(":")[1].lower()
    else:
        return display_name.lower()


def get_dname(e_name, e_id):
    return "<:" + e_name + ":" + str(e_id) + ">"


# TODO: Investigate standard emotes not working
def is_emoji(s):
    return False
    # return s in UNICODE_EMOJI


def score_algorithm(emoji_count):
    return round(0.61 + (1.37 * math.log(emoji_count)))


async def add_emote(display_name):
    key = dname_to_key(display_name)
    with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
        if key not in s_all_time:
            s_all_time[key] = Emoji(key, display_name)
        s_all_time[key].update_emote(display_name)

    await ut.botChannel.send(f"'{key}' has been added to the database!")


async def remove_emote(display_name):
    key = dname_to_key(display_name)
    with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
        s_all_time[key].deleted = True
        if s_all_time[key].score == 0:
            del s_all_time[key]

    await ut.botChannel.send(f"'{key}' has been deleted from the database!")


# Helper function that allows us to grab values from shelve without opening+closing
def get_emote(key):
    with shelve.open("./database/all_time_georgechamp_shelf.db") as s_all_time:
        return s_all_time.get(key)


# Helper function that allows us to grab values from shelve without opening+closing
def get_all_emotes():
    with shelve.open("./database/all_time_georgechamp_shelf.db") as s_all_time:
        return dict(s_all_time)


async def init_emote_leaderboard():
    with shelve.open("./database/starting_date_shelf.db") as starting_date:
        if "date" not in starting_date:
            today = date.today()
            starting_date["date"] = today.strftime("%d/%m/%Y")

    # Accounts for if emotes are added when bot is offline
    for emoji in ut.guildObject.emojis:
        key = dname_to_key(emoji.name)
        emote = get_emote(key)
        if emote is None or emote.deleted:
            display_name = get_dname(emoji.name, emoji.id)
            await add_emote(display_name)

    # Accounts for if emotes are deleted when bot is offline
    cached_emotes = get_all_emotes()
    for key in cached_emotes:
        curr_emote_keys = [dname_to_key(emoji.name) for emoji in ut.guildObject.emojis]
        emote = get_emote(key)
        if key not in curr_emote_keys and not emote.deleted:
            await remove_emote(emote.display_name)


def update_counts(display_name, increment=1):
    key = dname_to_key(display_name)
    with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
        if s_all_time[key].w_score + increment <= WEEKLY_EMOTE_LIMIT:
            s_all_time[key].award(increment)
        else:
            s_all_time[key].award(WEEKLY_EMOTE_LIMIT - s_all_time[key].w_score)


async def announcement_task():
    channel = ut.mainChannel
    try:
        shelf_as_dict = get_all_emotes().items()
        most_used_emotes = sorted(shelf_as_dict, key=lambda item: item[1].w_score, reverse=True)[:7]

        most_used_emotes = [
            (emote[1].display_name, emote[1].w_score) for emote in most_used_emotes if emote[1].w_score != 0
        ]

        if len(most_used_emotes) == 0:
            leaderboard_msg = "No emotes were used this week. :("
        else:
            leaderboard_msg = "Weekly emote update: \nEmote - Score \n"
            for i in range(7):
                if i < len(most_used_emotes):
                    leaderboard_msg += (
                        str(i + 1) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"
                    )

        await channel.send(leaderboard_msg)

        with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
            for key in s_all_time:
                s_all_time[key].w_score = 0

    except Exception as e:
        await channel.send("Error Printing Weekly Leaderboard: " + str(e))


async def get_emote_count_text(display_name: str) -> str:
    try:
        key = dname_to_key(display_name)
        all_emotes = get_all_emotes()
        if key in all_emotes:
            emote = all_emotes[key]
            return f"{emote.display_name} has been used {emote.score} times."
        return "I couldn't find the emote you were looking for"

    except Exception as e:
        return f"Error Printing Count: {e}"


async def get_leaderboard_text(page: int = 1, show_last: bool = False, show_deleted: bool = False) -> str:
    try:
        shelf_as_dict = get_all_emotes()
        most_used_emotes = sorted(shelf_as_dict.items(), key=lambda item: item[1].score, reverse=True)

        # Filter: only emotes with score != 0, then deleted-or-not based on flag
        filtered = []
        for emote in most_used_emotes:
            if emote[1].score != 0:
                if not emote[1].deleted and not show_deleted:
                    filtered.append((emote[1].display_name, emote[1].score))
                elif emote[1].deleted and show_deleted:
                    filtered.append((emote[1].key, emote[1].score))

        # FUTURE: when is_emoji() is fixed (see TODO at top of file), the
        # original design pushed low-score Unicode emojis off the front pages
        # so custom server emotes stayed prominent on page 1. Concretely:
        # compute the score of the (total_custom_emotes - 9)th custom emote
        # and filter Unicode emojis below that threshold out of `filtered`.
        # The previous implementation was broken (subscripted a dict-items
        # view) and never fired because is_emoji() is currently a no-op.
        # Reintroduce with a correct implementation when standard-emoji
        # tracking is restored.

        total_items = len(filtered)
        total_page_num = max(1, math.ceil(total_items / 10))

        if show_last:
            page = total_page_num
        page = max(1, page)

        start = (page - 1) * 10
        end = start + 10
        page_slice = filtered[start:end]

        if len(page_slice) == 0:
            return "Doesn't look like there are emojis here :( Try another page."

        with shelve.open("./database/starting_date_shelf.db") as starting_date:
            leaderboard_msg = "Leaderboard (" + starting_date["date"] + ")\nEmote - Score \n"
        for i in range(10):
            if i < len(page_slice):
                placement = start + i + 1
                leaderboard_msg += str(placement) + ". " + page_slice[i][0] + " - " + str(page_slice[i][1]) + "\n"
        leaderboard_msg += "Page " + str(page) + "/" + str(total_page_num)
        return leaderboard_msg

    except Exception as e:
        return f"Error Printing Leaderboard: {e}"


async def check_emoji(message):
    try:
        custom_emojis = re.findall(r"<:\w*:\d*>", message.content)

        emoji_names = list(Counter(custom_emojis).keys())
        emoji_counts = list(Counter(custom_emojis).values())

        for i in range(len(emoji_names)):
            for emoji in ut.guildObject.emojis:
                temp_emoji = emoji_names[i][1:][:-1].split(":", 2)
                if temp_emoji[1] == emoji.name and temp_emoji[2] == str(emoji.id) and emoji.animated is False:
                    update_counts(emoji_names[i], round(score_algorithm(emoji_counts[i])))

        unicode_emojis = unicode_emojis = [char for char in message.content if is_emoji(char)]
        emoji_names = list(Counter(unicode_emojis).keys())
        emoji_counts = list(Counter(unicode_emojis).values())
        for i in range(len(emoji_names)):
            update_counts(emoji_names[i], round(score_algorithm(emoji_counts[i])))

    except Exception as e:
        await message.channel.send("Error Checking Emote: " + str(e))


async def check_reaction(payload):
    channel = ut.get_channel(payload.channel_id)
    try:
        if payload.emoji.is_custom_emoji() and not payload.emoji.animated:
            for emoji in ut.guildObject.emojis:
                if payload.emoji.name == emoji.name and payload.emoji.id == emoji.id:
                    reaction_emoji_key = get_dname(payload.emoji.name, payload.emoji.id)
                    update_counts(reaction_emoji_key)
        elif is_emoji(payload.emoji.name):
            update_counts(payload.emoji.name)

    except Exception as e:
        await channel.send("Error Checking Reaction: " + str(e))


async def rename_emote(before, after):
    channel = ut.mainChannel
    try:
        before_dnames = {get_dname(emoji.name, emoji.id) for emoji in before}
        after_dnames = {get_dname(emoji.name, emoji.id) for emoji in after}

        # If user deleted emote
        deleted_names = before_dnames - after_dnames
        for deleted_name in deleted_names:
            await remove_emote(deleted_name)

        # If user added emote
        added_names = after_dnames - before_dnames
        for added_name in added_names:
            await add_emote(added_name)

    except Exception as e:
        await channel.send("Error Renaming Emotes: " + str(e))


async def transfer_emote_score(transfer_from: str, transfer_to: str) -> str:
    try:
        to_key = dname_to_key(transfer_to)
        from_key = dname_to_key(transfer_from)

        with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
            if (
                from_key in s_all_time
                and to_key in s_all_time
                and s_all_time[from_key].deleted
                and not s_all_time[to_key].deleted
            ):
                s_all_time[to_key].score += s_all_time[from_key].score
                del s_all_time[from_key]
                return f"Transfer from {transfer_from} to {s_all_time[to_key].display_name} successful!"
            return "Couldn't Transfer Emotes!"
    except Exception as e:
        return f"Error Transferring: {e}"


async def delete_emote_entry(deleted_emote: str) -> str:
    try:
        deleted_key = dname_to_key(deleted_emote)

        with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
            if deleted_key in s_all_time and s_all_time[deleted_key].deleted:
                del s_all_time[deleted_key]
                return "Deleted " + deleted_emote
            return "Couldn't find " + deleted_emote
    except Exception as e:
        return f"Error Deleting Emote: {e}"


async def add_emote_score(emote: str, score: int) -> str:
    try:
        emote_key = dname_to_key(emote)

        with shelve.open("./database/all_time_georgechamp_shelf.db", writeback=True) as s_all_time:
            if emote_key in s_all_time:
                s_all_time[emote_key].score += score
                return (
                    f"Added {score} to {s_all_time[emote_key].display_name}. New value is {s_all_time[emote_key].score}"
                )
            return f"Couldn't find {emote_key}"
    except Exception as e:
        return f"Error Adding Score to Emote: {e}"


async def active_emote_autocomplete(interaction, current: str):
    matches = []
    for key, emote in get_all_emotes().items():
        if emote.deleted:
            continue
        if current.lower() in key.lower() or current.lower() in emote.display_name.lower():
            matches.append(emote)

    matches.sort(key=lambda e: e.score, reverse=True)
    return [discord.app_commands.Choice(name=emote.key, value=emote.display_name) for emote in matches[:25]]


async def deleted_emote_autocomplete(interaction, current: str):
    matches = []
    for key, emote in get_all_emotes().items():
        if not emote.deleted:
            continue
        if current.lower() in key.lower():
            matches.append(emote)

    matches.sort(key=lambda e: e.score, reverse=True)
    return [discord.app_commands.Choice(name=f"{emote.key} (deleted)", value=emote.key) for emote in matches[:25]]
