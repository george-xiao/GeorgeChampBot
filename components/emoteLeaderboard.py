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
        elif s.get(key) is None or s[key]+increment <= WEEKLY_LIMIT:
            s_all_time[key] += increment
        else:
            s_all_time[key] += WEEKLY_LIMIT - s[key]

        if s.get(key) is None:
            s[key] = increment
        elif s[key]+increment <= WEEKLY_LIMIT:
            s[key] += increment
        else:
            s[key] += WEEKLY_LIMIT - s[key]
        return True
    except Exception as e:
        await message.channel.send('Error updating: ' + str(e))
        return False

async def announcement_task(channel, deleteAfter=None):
    try:
        s = shelve.open('./database/weekly_georgechamp_shelf.db')

        shelf_as_dict = dict(s)
        most_used_emotes = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)[:7]

        leaderboard_msg = "Weekly emote update: \nEmote - Score \n"
        for i in range(7):
            if (i < len(most_used_emotes)):
                leaderboard_msg = leaderboard_msg + str(i + 1) + ". " + most_used_emotes[i][0] + " - " + str(most_used_emotes[i][1]) + "\n"

        await channel.send(leaderboard_msg, delete_after=deleteAfter)

        if deleteAfter == None:
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
        most_used_emotes = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)
        total_custom_emotes = 0
        emote_limit = 0
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
        if len(message.content) != len('!leaderboard') and (message.content[len('!leaderboard') + 1:].strip().lower() != "last"):
                increment = int(message.content[len('!leaderboard') + 1:])
                # page size = 10
                start += (increment - 1) * 10
                end += (increment - 1) * 10
        curr_page_num = (start / 10) + 1

        total_page_num = 0
        for key in s_all_time:
            if not (is_emoji(key) and s_all_time[key] < emote_limit):
                total_page_num += 1
        if len(message.content) != len('!leaderboard') and (message.content[len('!leaderboard') + 1:].strip().lower() == "last"):
            end = total_page_num
            start = total_page_num - 10
            curr_page_num = math.ceil(total_page_num/10)
        total_page_num = math.ceil(total_page_num/10)

        temp = []
        for key in most_used_emotes:
            if not (is_emoji(key[0]) and s_all_time[key[0]] < emote_limit):
                temp.append(key)
        most_used_emotes = temp[start:end]

        if len(most_used_emotes) == 0:
            await message.channel.send("Doesn't look like there are emojis here :( Try another page.")
        else:
            leaderboard_msg = "Leaderboard (" + starting_date["date"] + ")\nEmote - Score \n"
            for i in range(10):
                # Standard emojis are not printed on the last page
                if (i < len(most_used_emotes) and not (is_emoji(most_used_emotes[i][0]) and most_used_emotes[i][1] < emote_limit)):
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
                temp_emoji = emoji_names[i][1:][:-1].split(':', 2)
                if temp_emoji[1] == emoji.name and temp_emoji[2] == str(emoji.id) and emoji.animated == False:
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

async def check_reaction(payload, guild, channel):
    try:
        s = shelve.open('./database/weekly_georgechamp_shelf.db')
        s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
        starting_date = shelve.open('./database/starting_date_shelf.db')

        if "date" not in starting_date:
            today = date.today()
            starting_date["date"] = today.strftime("%d/%m/%Y")
            
        if payload.emoji.is_custom_emoji() and not payload.emoji.animated:
            for emoji in guild.emojis:
                if payload.emoji.name == emoji.name and payload.emoji.id == emoji.id:
                    reaction_emoji_key = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
                    await updateCounts(s_all_time, s, reaction_emoji_key)
        elif is_emoji(payload.emoji.name):
            await updateCounts(s_all_time, s, payload.emoji.name)

        s.close()
        s_all_time.close()
    except Exception as e:
        await message.channel.send('Error Checking Reaction: ' + str(e))

async def transfer_emotes(transfer_from,transfer_to):
    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
    s = shelve.open('./database/weekly_georgechamp_shelf.db')

    # accounting for deleted emotes
    if s_all_time.get(transfer_from) is None and transfer_from[-1] == ":" and transfer_from[0] == ":" and len(transfer_from) > 2:
        transfer_from = "<" + transfer_from
        for temp in s_all_time:
            flag = True
            for i in range(len(transfer_from)):
                if i < len(temp) and temp[i] != transfer_from[i]:
                    flag = False
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
        
    if s.get(transfer_from) is not None:
        if s.get(transfer_to) is None:
            s[transfer_to] = s[transfer_from]
        else:
            s[transfer_to] += s[transfer_from]
        del s[transfer_from]

    return fromEmoteExists

async def rename_emote(channel,before,after):
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
                
        if added_emote is not None and deleted_emote is not None:
            await transfer_emotes(deleted_emote,added_emote)
    except Exception as e:
        await channel.send('Error Renaming Emotes: ' + str(e))

async def pls_transfer(message, adminRole):
    try:
        isAdmin = False
        for role in message.author.roles:
            if adminRole == role:
                isAdmin = True
                transfer_from = ((message.content.split(' ',1)[1]).split('->',1)[0]).strip()
                transfer_to = ((message.content.split(' ',1)[1]).split('->',1)[1]).strip()
                flag = await transfer_emotes(transfer_from,transfer_to)
                if flag:
                    await message.channel.send('Transfer Successful!')
                else:
                    await message.channel.send("Couldn't Transfer Emotes!")
        if not isAdmin:
            await message.channel.send('Admin Access Required. Ask a ' + adminRole.name)
    except Exception as e:
        await message.channel.send('Error Transferring: ' + str(e))

async def pls_delete(message, adminRole):
    try:
        isAdmin = False
        for role in message.author.roles:
            if adminRole == role:
                isAdmin = True
                s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
                s = shelve.open('./database/weekly_georgechamp_shelf.db')
                deleted_emote = message.content[11:]

                # accounting for deleted emotes
                if s_all_time.get(deleted_emote) is None and deleted_emote[-1] == ":" and deleted_emote[0] == ":" and len(deleted_emote) > 2:
                    deleted_emote = "<" + deleted_emote
                    for temp in s_all_time:
                        flag = True
                        for i in range(len(deleted_emote)):
                            if i < len(temp) and temp[i] != deleted_emote[i]:
                                flag = False
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
        if not isAdmin:
            await message.channel.send('Not an admin. Ask ' + adminRole.name)
    except Exception as e:
        await message.channel.send('Error Deleting: ' + str(e))
