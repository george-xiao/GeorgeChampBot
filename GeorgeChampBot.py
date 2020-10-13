import asyncio
from datetime import datetime
import discord
from dotenv import load_dotenv
import os

import emoteLeaderboard
import dotaReplay
import twitchAnnouncement
import musicPlayer

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

client = discord.Client()


async def find_channel(channel_name):
    guilds = client.guilds
    for guild in guilds:
        if guild.name == GUILD:
            for guild_channel in guild.channels:
                if guild_channel.name == channel_name:
                    # channel type = channel model
                    return guild_channel



@client.event
async def on_ready():
    guilds = client.guilds
    e_channel = ""
    georgechamp_emoji = None
    for guild in guilds:
        if guild.name == GUILD:
            for emoji in guild.emojis:
                if 'georgechamp' in emoji.name:
                    georgechamp_emoji = emoji

            for guild_channel in guild.channels:
                if guild_channel.name == ANNOUNCEMENT_CHANNEL:
                    # channel type = channel model
                    e_channel = guild_channel

    msg = await e_channel.send("GeorgeChampBot reporting for duty!")
    # assume only one emoji has georgechamp in it
    await msg.add_reaction(georgechamp_emoji.name + ":" + str(georgechamp_emoji.id))

    while 1:

        t_channel = await find_channel(WELCOME_CHANNEL)
        await twitchAnnouncement.check_twitch_live(t_channel, TWITCH_CLIENT_ID, TWITCH_OAUTH_TOKEN, twitch_user_list)
        # seconds/week
        curr_date = datetime.now()
        # if announcement time, assume it'll be on the hour e.g. 9:00am
        if curr_date.weekday() == ANNOUNCEMENT_DAY and curr_date.hour == ANNOUNCEMENT_HOUR and curr_date.minute == ANNOUNCEMENT_MIN:
            await emoteLeaderboard.announcement_task(e_channel)

        # what min of hour should u check
        elif curr_date.minute == 00 or curr_date.minute == 30:
            d_channel = await find_channel(DOTA_CHANNEL)
            await dotaReplay.check_recent_matches(d_channel, player_list, OPENDOTA_API_KEY)

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
        await emoteLeaderboard.print_count(message)
    elif message.content.startswith("!plsadd"):
        await musicPlayer.add_music(message)
    elif message.content.startswith("!plsplay"):
        await musicPlayer.play_music(message)
    elif message.content.startswith('!leaderboard'):
        await emoteLeaderboard.print_leaderboard(message)
    else:
        await emoteLeaderboard.check_emoji(message)


@client.event
async def on_raw_reaction_add(payload):
    await emoteLeaderboard.check_reaction(payload)


client.run(TOKEN)
