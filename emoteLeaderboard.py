from emoji import UNICODE_EMOJI
import math
import shelve
import operator
import re
from collections import Counter


def is_emoji(s):
    return s in UNICODE_EMOJI


def score_algorithm(emoji_count):
    return 0.61 + (1.37 * math.log(emoji_count))


def updateCounts(s_all_time, s, key, increment=1):
    try:
        if s.get(key) is None:
            s[key] = increment
        else:
            s[key] += increment

        if s_all_time.get(key) is None:
            s_all_time[key] = increment
        else:
            s_all_time[key] += increment

        return True
    except Exception:
        return False


async def announcement_task(channel):
    s = shelve.open('weekly_georgechamp_shelf.db')

    shelf_as_dict = dict(s)
    most_used_emotes = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)[:5]

    leaderboard_msg = "Weekly emote update: \nEmote - Score \n"
    for i in range(5):
        if (i < len(most_used_emotes)):
            leaderboard_msg = leaderboard_msg + str(i + 1) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"

    await channel.send(leaderboard_msg, delete_after=604800)

    s.clear()
    s.close()


async def print_count(message):
    s_all_time = shelve.open('all_time_georgechamp_shelf.db')

    try:
        requested_emote = message.content[10:]
        await message.channel.send(requested_emote + " has been used " + str(s_all_time[requested_emote]) + " times.")
    except KeyError:
        await message.channel.send("Looks like that emote hasn't been used yet.")
    except IndexError:
        await message.channel.send("Doesn't appear that you've added an emote, please add an emote to check.")

    s_all_time.close()


async def print_leaderboard(message):
    s_all_time = shelve.open('all_time_georgechamp_shelf.db')

    shelf_as_dict = dict(s_all_time)
    start = 0
    end = 10

    if len(message.content) != len('!leaderboard'):
        increment = int(message.content[len('!leaderboard') + 1:])
        # page size = 10
        start += (increment - 1) * 10
        end += (increment - 1) * 10

    curr_page_num = (start / 10) + 1
    total_page_num = math.ceil(len(dict(s_all_time).keys())/10)
    most_used_emotes = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)[start:end]

    if len(most_used_emotes) == 0:
        await message.channel.send("Doesn't look like there are emojis here :( Try another page.")
    else:
        leaderboard_msg = "All time leaderboard: - Page " + str(int(curr_page_num)) + "/" + str(int(total_page_num)) + "\nEmote - Score \n"
        for i in range(10):
            if (i < len(most_used_emotes)):
                placement = start + i + 1
                leaderboard_msg = leaderboard_msg + str(placement) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"

        await message.channel.send(leaderboard_msg)

    s_all_time.close()


async def check_emoji(message):
    s = shelve.open('weekly_georgechamp_shelf.db')
    s_all_time = shelve.open('all_time_georgechamp_shelf.db')

    custom_emojis = re.findall(r'<:\w*:\d*>', message.content)

    emoji_names = list(Counter(custom_emojis).keys())
    emoji_counts = list(Counter(custom_emojis).values())
    for i in range(len(emoji_names)):
        updateCounts(s_all_time, s, emoji_names[i], round(score_algorithm(emoji_counts[i])))

    unicode_emojis = []
    for character in message.content:
        if is_emoji(character):
            unicode_emojis.append(character)

    emoji_names = list(Counter(unicode_emojis).keys())
    emoji_counts = list(Counter(unicode_emojis).values())

    for i in range(len(emoji_names)):
        updateCounts(s_all_time, s, emoji_names[i], round(score_algorithm(emoji_counts[i])))

    s.close()
    s_all_time.close()


async def check_reaction(payload):
    s = shelve.open('weekly_georgechamp_shelf.db')
    s_all_time = shelve.open('all_time_georgechamp_shelf.db')

    if payload.emoji.is_custom_emoji():
        reaction_emoji_key = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
        updateCounts(s_all_time, s, reaction_emoji_key)
    elif payload.emoji.is_unicode_emoji():
        updateCounts(s_all_time, s, payload.emoji.name)

    s.close()
    s_all_time.close()
