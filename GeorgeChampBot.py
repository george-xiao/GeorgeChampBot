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
import twitch
import emoteLeaderboard
from random import randrange

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
# Announcement
ANNOUNCEMENT_CHANNEL = os.getenv('ANNOUNCEMENT_CHANNEL')
ANNOUNCEMENT_DAY = int(os.getenv('ANNOUNCEMENT_DAY'))
ANNOUNCEMENT_HOUR = int(os.getenv('ANNOUNCEMENT_HOUR'))
ANNOUNCEMENT_MIN = int(os.getenv('ANNOUNCEMENT_MIN'))
# Welcome
WELCOME_CHANNEL = os.getenv('WELCOME_CHANNEL')
WELCOME_ROLE = os.getenv("WELCOME_ROLE")
# Dotabuff
OPENDOTA_API_KEY = os.getenv('OPENDOTA_API_KEY')
DOTA_CHANNEL = os.getenv("DOTA_CHANNEL")
PLAYER_1_ID = os.getenv('PLAYER_1_ID')
PLAYER_2_ID = os.getenv('PLAYER_2_ID')
PLAYER_3_ID = os.getenv('PLAYER_3_ID')
PLAYER_4_ID = os.getenv('PLAYER_4_ID')
player_list = [PLAYER_1_ID, PLAYER_2_ID, PLAYER_3_ID, PLAYER_4_ID]
# Twitch
TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_USER_1 = os.getenv('TWITCH_USER_1')
TWITCH_USER_2 = os.getenv('TWITCH_USER_2')
twitch_user_list = [TWITCH_USER_1, TWITCH_USER_2]
twitch_curr_live = []

twitch_helix = twitch.TwitchHelix(client_id=TWITCH_CLIENT_ID, oauth_token=TWITCH_OAUTH_TOKEN)
client = discord.Client()
playlist = shelve.open("youtube_playlist_shelf.db")
played_playlist = shelve.open("youtube_played_playlist_shelf.db")

open_dota_players_url = "https://api.opendota.com/api/players/"


async def find_channel(channel_name):
    guilds = client.guilds
    for guild in guilds:
        if guild.name == GUILD:
            for guild_channel in guild.channels:
                if guild_channel.name == channel_name:
                    # channel type = channel model
                    return guild_channel


async def check_twitch_live():
    try:
        global twitch_curr_live
        channel = await find_channel(WELCOME_CHANNEL)
        res = twitch_helix.get_streams(user_logins=twitch_user_list)
        live_streams = []
        for stream_index in range(len(res)):
            live_streams.append(res[stream_index].user_name)
            if res[stream_index].user_name not in twitch_curr_live:
                await channel.send(res[stream_index].user_name + ' is live with ' + str(
                    res[stream_index].viewer_count) + ' viewers! Go support them at https://twitch.tv/' + res[
                                       stream_index].user_name)

        twitch_curr_live = live_streams
    except Exception as e:
        print(e)


async def check_recent_matches():
    curr_epoch_time = int(datetime.now().timestamp())
    channel = await find_channel(DOTA_CHANNEL)
    hed = {'Authorization': 'Bearer ' + OPENDOTA_API_KEY}
    for player in player_list:
        try:
            match_ids = []
            res = requests.get(open_dota_players_url + player + '/recentMatches', headers=hed)
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 3610s (1h + 10s)
                    if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 3610:
                        match_ids.append(str(match['match_id']))

                match_ids = list(dict.fromkeys(match_ids))
                for match_id in match_ids:
                    await channel.send(
                        "Looks like someone played a game... Here's the match:\nhttps://www.dotabuff.com/matches/" + str(
                            match_id))
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
        await check_twitch_live()
        # seconds/week
        curr_date = datetime.now()
        # if announcement time, assume it'll be on the hour e.g. 9:00am
        if curr_date.weekday() == ANNOUNCEMENT_DAY and curr_date.hour == ANNOUNCEMENT_HOUR and curr_date.minute == ANNOUNCEMENT_MIN:
            await emoteLeaderboard.announcement_task(channel)

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
        await channel.send(
            "Welcome " + member.display_name + " to :based: server where everyone pretends to be a racist")


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
        emoteLeaderboard.print_count(message)
    elif message.content.startswith("!plsadd"):
        songUrl = message.content[8:]
        flag = False
        for index in playlist:
            if playlist.get(index) == songUrl:
                flag = True
        if flag == False:
            playlist[str(len(dict(playlist)))] = songUrl
            await message.channel.send("Song added to the playlist!")
        else:
            await message.channel.send("Not added. Song is already in the playlist.")
    elif message.content.startswith("!plsplay"):
        randNum = str(randrange(0, len(playlist), 1))
        print(str(randNum))
        print(dict(playlist))
        print(dict(played_playlist))

        while randNum in played_playlist:
            randNum = await randrange(0, len(playlist), 1)
        played_playlist[playlist[randNum]] = playlist[randNum]
        if len(dict(playlist)) == len(dict(played_playlist)):
            played_playlist.clear()
        await message.channel.send("!play " + playlist[randNum])
    elif message.content.startswith('!leaderboard'):
        emoteLeaderboard.print_leaderboard(message)
    else:
        emoteLeaderboard.check_emoji(message)


@client.event
async def on_raw_reaction_add(payload):
    emoteLeaderboard.check_reaction(payload)


client.run(TOKEN)
