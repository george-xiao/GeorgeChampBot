from emoji import UNICODE_EMOJI
import math
import shelve
import operator
import re
from collections import Counter
from datetime import date

def is_emoji(s):
    return s in UNICODE_EMOJI


def score_algorithm(emoji_count):
    return 0.61 + (1.37 * math.log(emoji_count))


async def updateCounts(s_all_time, s, key, increment=1):
    WEEKLY_LIMIT = 250

    try:
        if s_all_time.get(key) is None:
            s_all_time[key] = increment
        elif s[key]+increment <= WEEKLY_LIMIT:
            s_all_time[key] += increment

        if s.get(key) is None:
            s[key] = increment
        elif s[key]+increment <= WEEKLY_LIMIT:
            s[key] += increment
        return True
    except Exception as e:
        await message.channel.send('Error updating: ' + str(e))
        return False


async def announcement_task(channel):
    try:
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
    except Exception as e:
        await channel.send('Error Printing Weakly Leaderboard: ' + str(e))


async def print_count(message):
    try:
        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

        try:
            requested_emote = message.content[10:]
            await message.channel.send(requested_emote + " has been used " + str(s_all_time[requested_emote]) + " times.")
        except KeyError:
            await message.channel.send("Looks like that emote hasn't been used yet.")
        except IndexError:
            await message.channel.send("Doesn't appear that you've added an emote, please add an emote to check.")

        s_all_time.close()
    except Exception as e:
        await message.channel.send('Error Printing Count: ' + str(e))


async def print_leaderboard(message):
    try:
        starting_date = shelve.open('./database/starting_date_shelf.db')
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

        total_page_num = 0
        for key in s_all_time:
            if not (is_emoji(key) and s_all_time[key] < 10):
                total_page_num += 1
        total_page_num = math.ceil(total_page_num/10)

        most_used_emotes = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)
        temp = []
        for key in most_used_emotes:
            if not (is_emoji(key[0]) and s_all_time[key[0]] < 10):
                temp.append(key)
        most_used_emotes = temp[start:end]

        if len(most_used_emotes) == 0:
            await message.channel.send("Doesn't look like there are emojis here :( Try another page.")
        else:
            leaderboard_msg = "Leaderboard (" + starting_date["date"] + ")\nEmote - Score \n"
            for i in range(10):
                # Standard emojis which have been used less than 10 times is not printed
                if (i < len(most_used_emotes) and not (is_emoji(most_used_emotes[i][0]) and most_used_emotes[i][1] < 10)):
                    placement = start + i + 1
                    leaderboard_msg = leaderboard_msg + str(placement) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"
            leaderboard_msg += "Page " + str(int(curr_page_num)) + "/" + str(int(total_page_num))
            await message.channel.send(leaderboard_msg)

        s_all_time.close()
    except Exception as e:
        await message.channel.send('Error Printing Leaderboard: ' + str(e))


async def check_emoji(message, guild):
    try:
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
                    await updateCounts(s_all_time, s, emoji_names[i], round(score_algorithm(emoji_counts[i])))

        unicode_emojis = []
        for character in message.content:
            if is_emoji(character):
                unicode_emojis.append(character)

        emoji_names = list(Counter(unicode_emojis).keys())
        emoji_counts = list(Counter(unicode_emojis).values())

        for i in range(len(emoji_names)):
            await updateCounts(s_all_time, s, emoji_names[i], round(score_algorithm(emoji_counts[i])))

        s.close()
        s_all_time.close()
    except Exception as e:
        await message.channel.send('Error Checking Emote: ' + str(e))


async def check_reaction(payload):
    s = shelve.open('./database/weekly_georgechamp_shelf.db')
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
    starting_date = shelve.open('./database/starting_date_shelf.db')

    shelf_as_dict = dict(starting_date)
    if len(shelf_as_dict) == 0:
        today = date.today()
        starting_date["date"] = today.strftime("%d/%m/%y")


    if payload.emoji.is_custom_emoji():
        reaction_emoji_key = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
        await updateCounts(s_all_time, s, reaction_emoji_key)
    elif payload.emoji.is_unicode_emoji():
        await updateCounts(s_all_time, s, payload.emoji.name)

    s.close()
    s_all_time.close()

async def transfer_emotes(transfer_from,transfer_to):
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

    # accounting for deleted emotes
    if s_all_time.get(transfer_from) is None:
        for temp in s_all_time:
            flag = True
            if len(temp) <= 1 or len(transfer_from) <= 1:
                flag = False
            else:
                for i in range(len(transfer_from)):
                    if (i+2) <= len(temp) and temp[i+1] != transfer_from[i]:
                        flag = False
                        break
            if flag == True:
                transfer_from = temp

    fromEmoteExists = False
    if s_all_time.get(transfer_from) is not None:
        fromEmoteExists = True
        if s_all_time.get(transfer_to) is None:
            s_all_time[transfer_to] = s_all_time[transfer_from]
        else:
            s_all_time[transfer_to] += s_all_time[transfer_from]
        del s_all_time[transfer_from]

    return fromEmoteExists

async def delete_emote(channel,before,after):
    try:
        deleted_emote = None
        for before_emote in before:
            flag = False
            for after_emote in after:
                if (after_emote.name == before_emote.name):
                    flag = True
            if(flag == False):
                deleted_emote = "<:" + before_emote.name + ":" + str(before_emote.id) + ">"
        # Added Mechanism for when the name of an emote is changed instead of deleted
        added_emote = None
        for after_emote in after:
            flag = False
            for before_emote in before:
                if (before_emote.name == after_emote.name):
                    flag = True
            if(flag == False):
                added_emote = "<:" + after_emote.name + ":" + str(after_emote.id) + ">"

        if added_emote is None and deleted_emote is not None:
            return
            # code for deleting the emote from the leaderboard after removing it from the server
            # try:
            #     s = shelve.open('./database/weekly_georgechamp_shelf.db')
            #     s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')

            #     if s.get(deleted_emote) is not None:
            #         del s[deleted_emote]

            #     if s_all_time.get(deleted_emote) is not None:
            #         del s_all_time[deleted_emote]
            # except:
            #     await channel.send("Error deleting emote from Leaderboard.")
        elif added_emote is not None and deleted_emote is not None:
            await transfer_emotes(deleted_emote,added_emote)
    except Exception as e:
        await channel.send('Error Renaming Emotes: ' + str(e))

async def pls_transfer(message, adminRole):
    try:
        transfer_from = ((message.content.split(' ',1)[1]).split('->',1)[0]).strip()
        transfer_to = ((message.content.split(' ',1)[1]).split('->',1)[1]).strip()

        for i in range(len(message.author.roles)):
            if adminRole == message.author.roles[i].name:
                flag = await transfer_emotes(transfer_from,transfer_to)
                if flag:
                    await message.channel.send('Transfer Successful!')
                else:
                    await message.channel.send("Couldn't Transfer Emotes!")
                return
        await message.channel.send('Admin Access Required. Ask a ' + adminRole)
    except Exception as e:
        await message.channel.send('Error Transferring: ' + str(e))

async def pls_delete(message, adminRole):
    try:
        for i in range(len(message.author.roles)):
            if adminRole == message.author.roles[i].name:
                s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
                s = shelve.open('./database/weekly_georgechamp_shelf.db')
                deleted_emote = message.content[11:]

                # accounting for deleted emotes
                if s_all_time.get(deleted_emote) is None:
                    for temp in s_all_time:
                        flag = True
                        if len(temp) <= 1 or len(deleted_emote) <= 1:
                            flag = False
                        else:
                            for i in range(len(deleted_emote)):
                                if (i+2) <= len(temp) and temp[i+1] != deleted_emote[i]:
                                    flag = False
                                    break
                        if flag == True:
                            deleted_emote = temp

                if s.get(deleted_emote) is not None:
                     del s[deleted_emote]
                if s_all_time.get(deleted_emote) is not None:
                    del s_all_time[deleted_emote]
                    await message.channel.send('Deleted ' + deleted_emote)
                else:
                    await message.channel.send("Couldn't find " + deleted_emote)

                s_all_time.close()
                s.close()
    except Exception as e:
        await message.channel.send('Error Deleting: ' + str(e))
