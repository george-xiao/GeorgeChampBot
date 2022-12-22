import math
import shelve
import re
from collections import Counter
from datetime import date
from emoji import UNICODE_EMOJI
import common.utils as ut


WEEKLY_EMOTE_LIMIT = 250


class Emoji:

    def __init__(self, key, display_name, score = 0):
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
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)

    key = dname_to_key(display_name)
    if key not in s_all_time:
        s_all_time[key] = Emoji(key, display_name)
    s_all_time[key].update_emote(display_name)

    s_all_time.close()
    await ut.botChannel.send(f"'{key}' has been added to the database!")


async def remove_emote(display_name):
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)

    key = dname_to_key(display_name)
    s_all_time[key].deleted = True
    if s_all_time[key].score == 0:
        del s_all_time[key]

    s_all_time.close()
    await ut.botChannel.send(f"'{key}' has been deleted from the database!")


# Helper function that allows us to grab values from shelve without opening+closing
def get_emote(key):
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
    emote = s_all_time[key] if key in s_all_time else None
    s_all_time.close()
    return emote

# Helper function that allows us to grab values from shelve without opening+closing
def get_all_emotes():
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
    shelf_as_dict = dict(s_all_time)
    s_all_time.close()
    return shelf_as_dict

async def init_emote_leaderboard():
    starting_date = shelve.open('./database/starting_date_shelf.db')
    if "date" not in starting_date:
        today = date.today()
        starting_date["date"] = today.strftime("%d/%m/%Y")
    starting_date.close()

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
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)

    key = dname_to_key(display_name)
    
    if s_all_time[key].w_score + increment <= WEEKLY_EMOTE_LIMIT:
        s_all_time[key].award(increment)
    else:
        s_all_time[key].award(WEEKLY_EMOTE_LIMIT - s_all_time[key].w_score)
    
    s_all_time.close()

async def announcement_task():
    channel = ut.mainChannel
    try:
        shelf_as_dict = get_all_emotes().items
        most_used_emotes = sorted(shelf_as_dict, key=lambda item: item[1].w_score, reverse=True)[:7]

        leaderboard_msg = "Weekly emote update: \nEmote - Score \n"
        for i in range(7):
            if i < len(most_used_emotes):
                leaderboard_msg = leaderboard_msg + str(i + 1) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"

        await channel.send(leaderboard_msg)

        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)
        for key in s_all_time:
            s_all_time[key].w_score = 0
        s_all_time.close()

    except Exception as e:
        await channel.send('Error Printing Weekly Leaderboard: ' + str(e))


async def print_count(message, display_name):
    try:
        key = dname_to_key(display_name)
        all_keys = get_all_emotes()
        if key in all_keys:
            emote = all_keys[key]
            await message.channel.send(emote.display_name + " has been used " + str(emote.score) + " times.")
        else:
            await message.channel.send("I couldn't find the emote you were looking for")

    except Exception as e:
        await message.channel.send('Error Printing Count: ' + str(e))


async def print_leaderboard(message, message_content):
    try:
        shelf_as_dict = get_all_emotes().items()
        most_used_emotes = sorted(shelf_as_dict, key=lambda item: item[1].score, reverse=True)
        total_custom_emotes = 0
        emote_limit = 0

        show_deleted = False
        message_content_list = message_content.split()
        if "-u" in message_content_list:
            show_deleted = True
            message_content_list.remove("-u")
        page_num = " ".join(message_content_list).strip()

        # Only list out non-deleted/deleted emotes, based on flag
        temp = []
        for emote in most_used_emotes:
            if emote[1].score != 0:
                if not emote[1].deleted and not show_deleted:
                    temp.append((emote[1].display_name, emote[1].score))
                elif emote[1].deleted and show_deleted:
                    temp.append((emote[1].key, emote[1].score))
        most_used_emotes = temp

        for key in most_used_emotes:
            if not is_emoji(key[0]):
                total_custom_emotes += 1
        counter = 0
        for key in most_used_emotes:
            if total_custom_emotes < 10:
                emote_limit = 99999999
                break            
            if counter == total_custom_emotes-9:
                emote_limit = key[1]+1
                break
            if not is_emoji(key[0]):
                counter += 1
        start = 0
        end = 10
        if page_num != "" and page_num != "last":
            increment = int(page_num)
            # page size = 10
            start += (increment - 1) * 10
            end += (increment - 1) * 10
        curr_page_num = (start / 10) + 1

        total_page_num = 0
        for key in shelf_as_dict:
            if not (is_emoji(key) and shelf_as_dict[key] < emote_limit):
                total_page_num += 1
        if page_num != "" and page_num != "last":
            end = total_page_num
            start = total_page_num - 10
            curr_page_num = math.ceil(total_page_num/10)
        total_page_num = math.ceil(total_page_num/10)

        temp = []
        for key in most_used_emotes:
            if not (is_emoji(key[0]) and shelf_as_dict[key[0]] < emote_limit):
                temp.append(key)
        most_used_emotes = temp[start:end]

        if len(most_used_emotes) == 0:
            await message.channel.send("Doesn't look like there are emojis here :( Try another page.")
        else:
            starting_date = shelve.open('./database/starting_date_shelf.db')
            leaderboard_msg = "Leaderboard (" + starting_date["date"] + ")\nEmote - Score \n"
            starting_date.close()
            for i in range(10):
                # Standard emojis are not printed on the last page
                if (i < len(most_used_emotes) and not (is_emoji(most_used_emotes[i][0]) and most_used_emotes[i][1] < emote_limit)):
                    placement = start + i + 1
                    leaderboard_msg = leaderboard_msg + str(placement) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"
            leaderboard_msg += "Page " + str(int(curr_page_num)) + "/" + str(int(total_page_num))
            await message.channel.send(leaderboard_msg)

    except Exception as e:
        await message.channel.send('Error Printing Leaderboard: ' + str(e))


async def check_emoji(message):
    try:
        custom_emojis = re.findall(r'<:\w*:\d*>', message.content)

        emoji_names = list(Counter(custom_emojis).keys())
        emoji_counts = list(Counter(custom_emojis).values())

        for i in range(len(emoji_names)):
            for emoji in ut.guildObject.emojis:
                temp_emoji = emoji_names[i][1:][:-1].split(':', 2)
                if temp_emoji[1] == emoji.name and temp_emoji[2] == str(emoji.id) and emoji.animated is False:
                    update_counts(emoji_names[i], round(score_algorithm(emoji_counts[i])))

        unicode_emojis = []
        for character in message.content:
            if is_emoji(character):
                unicode_emojis.append(character)
        emoji_names = list(Counter(unicode_emojis).keys())
        emoji_counts = list(Counter(unicode_emojis).values())
        for i in range(len(emoji_names)):
            update_counts(emoji_names[i], round(score_algorithm(emoji_counts[i])))

    except Exception as e:
        await message.channel.send('Error Checking Emote: ' + str(e))


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
        await channel.send('Error Checking Reaction: ' + str(e))

    
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
        await channel.send('Error Renaming Emotes: ' + str(e))


async def pls_transfer(message, message_content, admin_role):
    try:
        if not ut.author_is_admin(message.author, admin_role):
            await message.channel.send('Admin Access Required. Ask a ' + admin_role)
            return
            
        transfer_from, transfer_to = message_content.split(" ")
        to_key = dname_to_key(transfer_to)
        from_key = dname_to_key(transfer_from)

        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)
        if from_key in s_all_time and to_key in s_all_time and s_all_time[from_key].deleted and not s_all_time[to_key].deleted:
            s_all_time[to_key].score += s_all_time[from_key].score
            del s_all_time[from_key]
            await message.channel.send('Transfer Successful!')
        else:
            await message.channel.send("Couldn't Transfer Emotes!")
        s_all_time.close()

    except Exception as e:
        await message.channel.send('Error Transferring: ' + str(e))

async def pls_delete(message, deleted_emote, admin_role):
    try:
        if not ut.author_is_admin(message.author, admin_role):
            await message.channel.send('Admin Access Required. Ask a ' + admin_role)
            return

        deleted_key = dname_to_key(deleted_emote)

        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)
        if deleted_key in s_all_time and s_all_time[deleted_key].deleted:
            del s_all_time[deleted_key]
            await message.channel.send('Deleted ' + deleted_emote)
        else:
            await message.channel.send("Couldn't find " + deleted_emote)
        s_all_time.close()
        
    except Exception as e:
        await message.channel.send('Error Deleting Emote: ' + str(e))

async def plsaddscore_h(message, message_content, admin_role):
    try:
        if not ut.author_is_admin(message.author, admin_role):
            await message.channel.send('Admin Access Required. Ask a ' + admin_role)
            return

        emote, score = message_content.split()
        emote_key = dname_to_key(emote)

        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db', writeback=True)
        if emote_key in s_all_time:
            s_all_time[emote_key].score += int(score)
            await message.channel.send(f"Added {score} to {emote_key}. New value is {s_all_time[emote_key].score}")
        else:
            await message.channel.send("Couldn't find " + emote_key)
        s_all_time.close()
        
    except Exception as e:
        await message.channel.send('Error Adding Score to Emote: ' + str(e))