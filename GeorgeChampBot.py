# GeorgeChampBot.py

import asyncio
from collections import Counter
from datetime import datetime
import discord
from dotenv import load_dotenv
from emoji import UNICODE_EMOJI
import math
import operator
import os
import re
import requests
import shelve

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
ANNOUNCEMENT_CHANNEL = os.getenv('ANNOUNCEMENT_CHANNEL')
ANNOUNCEMENT_DAY = int(os.getenv('ANNOUNCEMENT_DAY'))
ANNOUNCEMENT_HOUR = int(os.getenv('ANNOUNCEMENT_HOUR'))
ANNOUNCEMENT_MIN = int(os.getenv('ANNOUNCEMENT_MIN'))
WELCOME_CHANNEL = os.getenv('WELCOME_CHANNEL')
WELCOME_ROLE = os.getenv("WELCOME_ROLE")
OPENDOTA_API_KEY = os.getenv('OPENDOTA_API_KEY')
DOTA_CHANNEL = os.getenv("DOTA_CHANNEL")
PLAYER_1_ID = os.getenv('PLAYER_1_ID')
PLAYER_2_ID = os.getenv('PLAYER_2_ID')
PLAYER_3_ID = os.getenv('PLAYER_3_ID')
PLAYER_4_ID = os.getenv('PLAYER_4_ID')
player_list = [PLAYER_1_ID, PLAYER_2_ID, PLAYER_3_ID, PLAYER_4_ID]


client = discord.Client()
s = shelve.open('weekly_georgechamp_shelf.db')
s_all_time = shelve.open('all_time_georgechamp_shelf.db')
dota_shelf = shelve.open('dota_shelf.db')

open_dota_players_url = "https://api.opendota.com/api/players/"

def score_algorithm(emoji_count):
    return 0.61 + (1.37 * math.log(emoji_count))


def updateCounts(key, increment = 1):
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


def is_emoji(s):
    return s in UNICODE_EMOJI


async def find_channel(channel_name):
    guilds = client.guilds
    for guild in guilds:
        if guild.name == GUILD:
            for guild_channel in guild.channels:
                if guild_channel.name == channel_name:
                    # channel type = channel model
                    return guild_channel


async def announcement_task():
    print("it rly should print :)")
    guilds = client.guilds
    channel = await find_channel(ANNOUNCEMENT_CHANNEL)

    shelf_as_dict = dict(s)
    most_used_emotes = dict(sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)[:5])

    keys = []
    key_vals = []
    for key in most_used_emotes.keys():
        keys.append(key)
        key_vals.append(most_used_emotes[key])

    leaderboard_msg = "Weekly emote update: \nEmote - Score \n"
    for i in range(5):
        if (i < len(keys)):
            leaderboard_msg = leaderboard_msg + str(i + 1) + ". " + keys[i] + " - " + str(key_vals[i]) + "\n"

    await channel.send(leaderboard_msg)

    s.clear()


async def check_recent_matches():
    curr_epoch_time = int(datetime.now().timestamp())
    channel = await find_channel(DOTA_CHANNEL)
    match_ids = []
    dota_shelf_as_dict = dict(dota_shelf)
    hed = {'Authorization': 'Bearer ' + OPENDOTA_API_KEY}
    for player in player_list:
        try:
            res = requests.get(open_dota_players_url + player + '/recentMatches', headers=hed)
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 1h + 10s
                    if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 3610:
                        match_ids.append(str(match['match_id']))

                for match_id in match_ids:
                    if dota_shelf.get(match_id) is None:
                        await channel.send("Looks like someone played a game... Here's the match:\nhttps://www.dotabuff.com/matches/" + str(match_id))
                        dota_shelf[match_id] = 1
        except Exception as e:
            await channel.send("Looks like the opendota api is down or ur code is bugged. George pls fix.")



@client.event
async def on_ready():
    guilds = client.guilds
    channel = ""
    georgechamp_emoji = None
    for guild in guilds:
        if guild.name == GUILD:
            for emoji in guild.emojis:
                if 'georgechamp' in emoji.name:
                    georgechamp_emoji = emoji

            for guild_channel in guild.channels:
                if guild_channel.name == ANNOUNCEMENT_CHANNEL:
                    # channel type = channel model
                    channel = guild_channel

    msg = await channel.send("GeorgeChampBot reporting for duty!")
    # assume only one emoji has georgechamp in it
    await msg.add_reaction(georgechamp_emoji.name + ":" + str(georgechamp_emoji.id))

    while 1:
        # seconds/week
        curr_date = datetime.now()
        # if announcement time, assume it'll be on the hour e.g. 9:00am
        if curr_date.weekday() == ANNOUNCEMENT_DAY and curr_date.hour == ANNOUNCEMENT_HOUR and curr_date.minute == ANNOUNCEMENT_MIN:
            await announcement_task()

        # what min of hour should u check
        elif curr_date.minute == 00:
            await check_recent_matches()

        await asyncio.sleep(55)

@client.event
async def on_member_join(member):
    channel = await find_channel(WELCOME_CHANNEL)
    try:
        await member.add_roles(discord.utils.get(member.guild.roles, name=WELCOME_ROLE))
    except Exception as e:
        await channel.send('There was an error running this command ' + str(e))  # if error
    else:
        await channel.send("Welcome " + member.display_name + " to :based: server where everyone pretends to be a racist")


@client.event
async def on_disconnect():
    channel = await find_channel(WELCOME_CHANNEL)
    try:
        await channel.send("GeorgeChampBot signing out!")
    except Exception:
        await channel.send("I believe I am leaving but something went wrong... Blame George.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return None
    elif message.content.startswith('!plshelp'):
        try:
            help_msg = "List of commands:\n!plshelp - This.\n!plscount <emote> - All time score of <emote>\n!leaderboard <page#> - All time scores"
            await message.channel.send(help_msg)
        except Exception:
            await message.channel.send("Something went wrong... It's not your fault though, blame George.")
    elif message.content.startswith('!plscount'):
        try:
            requested_emote = message.content[10:]
            await message.channel.send(requested_emote + " has been used " + str(s_all_time[requested_emote]) + " times.")
        except KeyError:
            await message.channel.send("Looks like that emote hasn't been used yet.")
        except IndexError:
            await message.channel.send("Doesn't appear that you've added an emote, please add an emote to check.")
    elif message.content.startswith('!leaderboard'):
        shelf_as_dict = dict(s_all_time)
        start = 0
        end = 10

        if len(message.content) != len('!leaderboard'):
            increment = int(message.content[len('!leaderboard')+1:])
            # page size = 10
            start += (increment - 1) * 10
            end += (increment - 1) * 10

        curr_page_num = (start / 10) + 1
        total_page_num = len(dict(s_all_time).keys())/10 + 1
        most_used_emotes = dict(sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)[start:end])
        keys = []
        key_vals = []
        for key in most_used_emotes.keys():
            keys.append(key)
            key_vals.append(most_used_emotes[key])

        if len(keys) == 0:
            await message.channel.send("Doesn't look like there are emojis here :trisad2:. Try another page.")
        else:
            leaderboard_msg = "All time leaderboard: - Page " + str(int(curr_page_num)) + "/" + str(int(total_page_num)) + "\nEmote - Score \n"
            for i in range(10):
                if (i < len(keys)):
                    placement = start + i + 1
                    leaderboard_msg = leaderboard_msg + str(placement) + ". " + keys[i] + " - " + str(key_vals[i]) + "\n"

            await message.channel.send(leaderboard_msg)
    else:
        custom_emojis = re.findall(r'<:\w*:\d*>', message.content)

        emoji_names = list(Counter(custom_emojis).keys())
        emoji_counts = list(Counter(custom_emojis).values())
        for i in range(len(emoji_names)):
            updateCounts(emoji_names[i], round(score_algorithm(emoji_counts[i])))

        unicode_emojis = []
        for character in message.content:
            if is_emoji(character):
                unicode_emojis.append(character)

        emoji_names = list(Counter(unicode_emojis).keys())
        emoji_counts = list(Counter(unicode_emojis).values())

        for i in range(len(emoji_names)):
            updateCounts(emoji_names[i], round(score_algorithm(emoji_counts[i])))


@client.event
async def on_raw_reaction_add(payload):
    if (payload.emoji.is_custom_emoji()):
        reaction_emoji_key = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
        updateCounts(reaction_emoji_key)
    elif payload.emoji.is_unicode_emoji():
        updateCounts(payload.emoji.name)


client.run(TOKEN)
s.close('weekly_georgechamp_shelf.db')
s_all_time.close('all_time_georgechamp_shelf.db')
