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
    s = shelve.open('./database/weekly_georgechamp_shelf.db')

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
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

    try:
        requested_emote = message.content[10:]
        await message.channel.send(requested_emote + " has been used " + str(s_all_time[requested_emote]) + " times.")
    except KeyError:
        await message.channel.send("Looks like that emote hasn't been used yet.")
    except IndexError:
        await message.channel.send("Doesn't appear that you've added an emote, please add an emote to check.")

    s_all_time.close()


async def print_leaderboard(message):
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

    shelf_as_dict = dict(s_all_time)
    start = 0
    end = 10

    if len(message.content) != len('!leaderboard'):
        if(message.content[len('!leaderboard') + 1:].strip().lower() == "last"):
            end = len(shelf_as_dict)
            start = end - 10
        else:
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


async def check_emoji(message, guild):
    s = shelve.open('./database/weekly_georgechamp_shelf.db')
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

    custom_emojis = re.findall(r'<:\w*:\d*>', message.content)
    check_emoji_name = list(Counter(custom_emojis).keys())

    emoji_names = list(Counter(custom_emojis).keys())
    emoji_counts = list(Counter(custom_emojis).values())

    for i in range(len(emoji_names)):
        for emoji in guild.emojis:
            temp_emoji = emoji_names[i].split(':', 2)
            if temp_emoji[1] in emoji.name:
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
    s = shelve.open('./database/weekly_georgechamp_shelf.db')
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

    if payload.emoji.is_custom_emoji():
        reaction_emoji_key = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
        updateCounts(s_all_time, s, reaction_emoji_key)
    elif payload.emoji.is_unicode_emoji():
        updateCounts(s_all_time, s, payload.emoji.name)

    s.close()
    s_all_time.close()

async def transfer_emotes(transfer_from,transfer_to):
        s = shelve.open('./database/weekly_georgechamp_shelf.db')
        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

        if s.get(transfer_to) is None:
            s[transfer_to] = s[transfer_from]
        else:
            s[transfer_to] += s[transfer_from]
        del s[transfer_from]

        if s_all_time.get(transfer_to) is None:
            s_all_time[transfer_to] = s_all_time[transfer_from]
        else:
            s_all_time[transfer_to] += s_all_time[transfer_from]
        del s_all_time[transfer_from]

async def delete_emote(channel,before,after):
    deleted_emote = None
    for before_emote in before:
        flag = False
        for after_emote in after:
            if (after_emote.name == before_emote.name):
                flag = True
        if(flag == False):
            deleted_emote = "<:" + before_emote.name + ":" + str(before_emote.id) + ">"

    #Added Mechanism for when the name of an emote is changed instead of deleted
    added_emote = None
    for after_emote in after:
        flag = False
        for before_emote in before:
            if (before_emote.name == after_emote.name):
                flag = True
        if(flag == False):
            added_emote = "<:" + after_emote.name + ":" + str(after_emote.id) + ">"

    if(added_emote is None):
        try:
            s = shelve.open('./database/weekly_georgechamp_shelf.db')
            s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

            if s.get(deleted_emote) is not None:
                del s[deleted_emote]

            if s_all_time.get(deleted_emote) is not None:
                del s_all_time[deleted_emote]
        except:
            await channel.send("Error deleting emote from Leaderboard. Maaz fix pls")
    else:
        try:
            await transfer_emotes(deleted_emote,added_emote)
        except:
            await channel.send("Error updating the Leaderboard when renaming emote. Maaz fix pls")
