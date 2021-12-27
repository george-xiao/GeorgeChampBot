import asyncio
from asyncio.windows_events import NULL
from datetime import datetime
import discord
from discord import channel
from discord.client import Client
from dotenv import load_dotenv
from discord.ext import commands
import os

from discord.utils import get
from components import emoteLeaderboard, dotaReplay, twitchAnnouncement, musicPlayer, memeReview, music


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
ADMIN_ROLE = os.getenv('ADMIN_ROLE')
MAIN_CHANNEL = os.getenv('MAIN_CHANNEL')
BOT_CHANNEL = os.getenv('BOT_CHANNEL')
# Announcement
ANNOUNCEMENT_CHANNEL = os.getenv('ANNOUNCEMENT_CHANNEL')
ANNOUNCEMENT_DAY = int(os.getenv('ANNOUNCEMENT_DAY'))
ANNOUNCEMENT_HOUR = int(os.getenv('ANNOUNCEMENT_HOUR'))
ANNOUNCEMENT_MIN = int(os.getenv('ANNOUNCEMENT_MIN'))
# Welcome
WELCOME_ROLE = os.getenv("WELCOME_ROLE")
# Dotabuff
OPENDOTA_API_KEY = os.getenv('OPENDOTA_API_KEY')
DOTA_CHANNEL = os.getenv("DOTA_CHANNEL")
PLAYER_1_ID = os.getenv('PLAYER_1_ID')
PLAYER_2_ID = os.getenv('PLAYER_2_ID')
PLAYER_3_ID = os.getenv('PLAYER_3_ID')
PLAYER_4_ID = os.getenv('PLAYER_4_ID')
player_list = [PLAYER_1_ID, PLAYER_2_ID, PLAYER_3_ID, PLAYER_4_ID]
prev_hour = False
# Twitch
TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_USER_1 = os.getenv('TWITCH_USER_1')
TWITCH_USER_2 = os.getenv('TWITCH_USER_2')
twitch_user_list = [TWITCH_USER_1, TWITCH_USER_2]
twitch_curr_live = []
# Meme Review
MEME_CHANNEL = os.getenv('MEME_CHANNEL')

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
api_running = False
guildObject = None
mainChannel = None
memeChannel = None

async def find_channel(channel_name):
    guilds = client.guilds
    for guild in guilds:
        if guild.name == GUILD:
            for guild_channel in guild.channels:
                if guild_channel.name == channel_name or guild_channel.id == channel_name:
                    # channel type = channel model
                    return guild_channel
                
async def get_guild():
    guilds = client.guilds
    for guild in guilds:
        if guild.name == GUILD:
            return guild

@client.event
async def on_ready():
    guilds = client.guilds
    georgechamp_emoji = None
    for guild in guilds:
        if guild.name == GUILD:
            global guildObject
            guildObject = guild
            for emoji in guild.emojis:
                if 'georgechamp' in emoji.name:
                    georgechamp_emoji = emoji

            for guild_channel in guild.channels:
                if guild_channel.name == MAIN_CHANNEL:
                    # channel type = channel model
                    global mainChannel
                    mainChannel = guild_channel
                    msg = await mainChannel.send("GeorgeChampBot reporting for duty!", delete_after=21600)
                    # assume only one emoji has georgechamp in it
                    # await msg.add_reaction(georgechamp_emoji.name + ":" + str(georgechamp_emoji.id))
                if guild_channel.name == MEME_CHANNEL:
                    global memeChannel
                    memeChannel = guild_channel

    if not(os.path.exists("database")):
        try:
            os.mkdir("./database")
        except:
            await mainChannel.send("Error creating Database.")

    global api_running
    global prev_hour
    if api_running is False:
        
        a_channel = await find_channel(ANNOUNCEMENT_CHANNEL)
        t_channel = await find_channel(MAIN_CHANNEL)
        
        # if announcement time, assume it'll be on the hour e.g. 9:00am
        
        while 1:
            api_running = True
            # seconds/week
            curr_date = datetime.now()
            
            if (curr_date.second % 55) == 0:
                await twitchAnnouncement.check_twitch_live(t_channel, TWITCH_CLIENT_ID, TWITCH_OAUTH_TOKEN, twitch_user_list)
                if curr_date.weekday() == ANNOUNCEMENT_DAY and curr_date.hour == ANNOUNCEMENT_HOUR and curr_date.minute == ANNOUNCEMENT_MIN:
                    await emoteLeaderboard.announcement_task(a_channel, 604800)
                    await emoteLeaderboard.announcement_task(mainChannel)
                if curr_date.weekday() == ((ANNOUNCEMENT_DAY-1)%7) and curr_date.hour == ANNOUNCEMENT_HOUR and curr_date.minute == ANNOUNCEMENT_MIN:
                    await memeReview.best_announcement_task(a_channel, 604800)
                    await memeReview.best_announcement_task(mainChannel)
                if curr_date.hour == 00 and curr_date.minute == 00:
                    await memeReview.resetLimit()
                # what min of hour should u check; prints only if the current games have not been printed
                if (prev_hour != curr_date.hour and curr_date.minute == 00):
                    d_channel = await find_channel(DOTA_CHANNEL)
                    prev_hour = curr_date.hour
                    try:
                        await dotaReplay.check_recent_matches(d_channel, player_list, OPENDOTA_API_KEY)
                    except:
                        api_running = False
            if (curr_date.second % 1) == 0:
                if (client.voice_clients is not None) and (len(client.voice_clients) > 0):
                    await music.play_song(client.voice_clients[0])
            await asyncio.sleep(1)


@client.event
async def on_member_join(member):
    channel = await find_channel(MAIN_CHANNEL)
    try:
        for role in guildObject.roles:
            tempAdminRole = WELCOME_ROLE
            if role.name[0] != "@":
                tempAdminRole = WELCOME_ROLE[1:]
            if role.name == tempAdminRole:
                await member.add_roles(discord.utils.get(member.guild.roles, name=role.name))
    except Exception as e:
        await channel.send('There was an error running this command ' + str(e))  # if error
    else:
        await channel.send("Welcome <@" + str(member.id) + "> to a wholesome server!")

@client.event
async def on_member_remove(member):
    channel = await find_channel(MAIN_CHANNEL)
    await channel.send(member.name + " has decided to leave us :(")

#@client.event
#async def on_disconnect():
#    channel = await find_channel(MAIN_CHANNEL)
#    try:
#        await channel.send("GeorgeChampBot signing out!")
#    except Exception:
#        await channel.send("I believe I am leaving but something went wrong... Blame George.")


@client.event
async def on_message(message):

    if message.author == client.user:
        return None
    elif message.content.startswith('!plshelp'):
        try:
            help_msg = "List of commands:\n!plshelp - This.\n!plscount <emote> - All time score of <emote>\n!leaderboard <page# OR 'last'> - All time scores\n!plstransfer <emoteFrom> -> <emoteTo> - Transfers emoteFrom to emoteTo (Admin Only)\n!plsdelete <emote> - Deletes emote from database (Admin Only)"
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
    elif message.content.startswith('!memerboard'):
        await memeReview.print_memerboard(message)
    elif message.content.startswith('!plsletmeplay'):
        await dotaReplay.print_tokens(message.channel)
    elif message.content.startswith('!plstransfer'):
        await emoteLeaderboard.pls_transfer(message, ADMIN_ROLE)
    elif message.content.startswith('!plsdelete'):
        await emoteLeaderboard.pls_delete(message, ADMIN_ROLE)
    elif message.content.startswith('!p'):
        await music.play(message)
    elif message.content.startswith('!pjoin'):
        await music.join(message)
    elif message.content.startswith('!pause'):
        await music.pause(message)
    elif message.content.startswith('!resume'):
        await music.resume(message)
    elif message.content.startswith('!queue'):
        await music.queue(message)
    elif message.content.startswith('!skip'):
        await music.skip(message)
    elif message.content.startswith('!disc'):
        await music.disconnect(message)   
             

    else:
        await memeReview.check_meme(message, guildObject, mainChannel, memeChannel)
        await emoteLeaderboard.check_emoji(message, guildObject)


@client.event
async def on_raw_reaction_add(payload):
    await emoteLeaderboard.check_reaction(payload, guildObject, mainChannel)
    await memeReview.add_meme_reactions(payload, memeChannel, guildObject, ADMIN_ROLE)

@client.event
async def on_raw_reaction_remove(payload):
    await memeReview.remove_meme_reactions(payload, memeChannel)

@client.event
async def on_guild_emojis_update(guild, before, after):
    await emoteLeaderboard.rename_emote(mainChannel,before,after)

client.run(TOKEN)
