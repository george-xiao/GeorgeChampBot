import asyncio
from datetime import datetime
import discord
from dotenv import load_dotenv
import os

from components import emoteLeaderboard, dotaReplay, music, twitchAnnouncement, memeReview


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
BOT_ID = os.getenv('BOT_ID')
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
# Twitch
TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_USER_1 = os.getenv('TWITCH_USER_1')
TWITCH_USER_2 = os.getenv('TWITCH_USER_2')
twitch_user_list = [TWITCH_USER_1, TWITCH_USER_2]
twitch_curr_live = []
# Meme Review
MEME_CHANNEL = os.getenv('MEME_CHANNEL')
# Music Bot
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

prev_hour = False
api_running = False
intents = discord.Intents.default()
intents.members = True

# Frequently used Objects
client = discord.Client(intents=intents)
botObject = None
guildObject = None
mainChannel = None


# Get channel object
def get_channel(channel_name):
    for guild_channel in guildObject.channels:
        if guild_channel.name == channel_name or str(guild_channel.id) == channel_name:
            return guild_channel

# Get role object
def get_role(role_name):
    for role in guildObject.roles:
        role_name_list = [role_name]
        if role_name[0] == "@":
            role_name_list.append(role_name[1:])
        else:
            role_name_list.append("@" + role_name)
        if role.name in role_name_list:
            return role

# Get member object
def get_member(member_name):
    for guild_member in guildObject.members:
        if guild_member.name == member_name or str(guild_member.id) == member_name:
            return guild_member

def init_globals():
    global guildObject
    for guild in client.guilds:
        if guild.name == GUILD:
            guildObject = guild

    global mainChannel
    mainChannel = get_channel(MAIN_CHANNEL)

    global botObject
    botObject = get_member(BOT_ID)

@client.event
async def on_ready():
    init_globals()

    georgechamp_emoji = None
    for emoji in guildObject.emojis:
        if 'georgechamp' in emoji.name:
            georgechamp_emoji = emoji

    msg = await mainChannel.send("GeorgeChampBot reporting for duty!", delete_after=21600)
    # await msg.add_reaction(georgechamp_emoji.name + ":" + str(georgechamp_emoji.id))

    if not(os.path.exists("database")):
        try:
            os.mkdir("./database")
        except:
            await mainChannel.send("Error creating Database.")

    global api_running
    global prev_hour
    if api_running is False:
        
        a_channel = get_channel(ANNOUNCEMENT_CHANNEL)
        
        while 1:
            api_running = True
            curr_date = datetime.now()
            
            if (curr_date.second % 55) == 0:
                # await twitchAnnouncement.check_twitch_live(mainChannel, TWITCH_CLIENT_ID, TWITCH_OAUTH_TOKEN, twitch_user_list)
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
                    d_channel = get_channel(DOTA_CHANNEL)
                    prev_hour = curr_date.hour
                    try:
                        await dotaReplay.check_recent_matches(d_channel, player_list, OPENDOTA_API_KEY)
                    except:
                        api_running = False

            if (curr_date.second % 1) == 0:
                await music.process_song(get_channel(BOT_CHANNEL), botObject)
                await music.play_song(get_channel(BOT_CHANNEL))

            await asyncio.sleep(1)


@client.event
async def on_member_join(member):
    try:
        await mainChannel.send("Welcome <@" + str(member.id) + "> to a wholesome server!")
        role = get_role(WELCOME_ROLE)
        await member.add_roles(discord.utils.get(member.guild.roles, name=role.name))
    except Exception as e:
        await mainChannel.send('There was an error running this command ' + str(e))  # if error


@client.event
async def on_member_remove(member):
    await mainChannel.send(member.name + " has decided to leave us :(")


#@client.event
async def on_disconnect():
   try:
            await music.disconnect(get_channel(BOT_CHANNEL))
    #    await mainChannel.send("GeorgeChampBot signing out!")
   except Exception:
       await mainChannel.send("I believe I am leaving but something went wrong... Blame George.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return None
    command_name = " ".join(message.content.lower().split()[:1])
    message_content = " ".join(message.content.split()[1:])

    music_commands = ['!p', '!play', '!pause', '!resume', '!queue', '!nowplaying', '!np', '!skip', '!disconnect', '!clear', '!shuffle', '!move', '!loop']
    if await music.is_valid_music_command(music_commands, botObject, message, get_channel(BOT_CHANNEL)):
        if command_name in ['!p', '!play']:
            await music.play(message, message_content, YOUTUBE_API_KEY)
        elif await music.bot_is_connected(message):
            if command_name in ['!pause']:
                await music.pause(message.channel)
            elif command_name in ['!resume']:
                await music.resume(message.channel)
            elif command_name in ['!queue']:
                await music.queue(message, message_content)
            elif command_name in ['!nowplaying', '!np']:
                await music.now_playing(message.channel)
            elif command_name in ['!skip', '!next']:
                await music.skip(message.channel)
            elif command_name in ['!clear']:
                await music.clear(message.channel)
            elif command_name in ['!disconnect']:
                await music.disconnect(message.channel)
            elif command_name in ['!shuffle']:
                await music.shuffle(message)
            elif command_name in ['!move']:
                await music.move(message, message_content)
            elif command_name in ['!loop']:
                await music.loop(message, message_content)
    elif command_name in ['!plshelp']:
        await print_help(message, message_content)
    elif command_name in ['!plscount']:
        await emoteLeaderboard.print_count(message)
    elif command_name in ['!leaderboard']:
        await emoteLeaderboard.print_leaderboard(message)
    elif command_name in ['!memerboard']:
        await memeReview.print_memerboard(message)
    elif command_name in ['!plsletmeplay']:
        await dotaReplay.print_tokens(message.channel)
    elif command_name in ['!plstransfer']:
        await emoteLeaderboard.pls_transfer(message, get_role(ADMIN_ROLE))
    elif command_name in ['!plsdelete']:
        await emoteLeaderboard.pls_delete(message, get_role(ADMIN_ROLE))
    else:
        await memeReview.check_meme(message, guildObject, mainChannel, get_channel(MEME_CHANNEL))
        await emoteLeaderboard.check_emoji(message, guildObject)


@client.event
async def on_raw_reaction_add(payload):
    is_meme = await memeReview.add_meme_reactions(payload, get_channel(MEME_CHANNEL), guildObject, get_role(ADMIN_ROLE))
    if not is_meme:
        await emoteLeaderboard.check_reaction(payload, guildObject, mainChannel)
    
@client.event
async def on_raw_reaction_remove(payload):
    await memeReview.remove_meme_reactions(payload, get_channel(MEME_CHANNEL))

@client.event
async def on_guild_emojis_update(guild, before, after):
    await emoteLeaderboard.rename_emote(mainChannel,before,after)

async def print_help(message, message_content):
    try:
        message_content = message_content.lower()
        help_msg = ""
        if message_content == "emote":
            help_msg += "Emote Leaderboard Commands\n"
            help_msg += "!plscount <emote> - All time score of <emote>\n"
            help_msg += "!leaderboard <page# OR 'last'> - All time emoji scores\n"
            help_msg += "!plstransfer <emoteFrom> -> <emoteTo> - Transfers emoteFrom to emoteTo (Admin Only)\n"
            help_msg += "!plsdelete <emote> - Deletes emote from database (Admin Only)\n"
        elif message_content == "music":
            help_msg += "Music Player Commands\n"
            help_msg += "!p <song> - Plays songs or playlists\n"
            help_msg += "!pause - Pauses the song\n"
            help_msg += "!resume - Resumes the song\n"
            help_msg += "!skip - Skips song\n"
            help_msg += "!np - Currently playing song\n"
            help_msg += "!queue <pageNumber> - Prints queue\n"
            help_msg += "!clear - Clears the queue\n"
            help_msg += "!disconnect - Disconnects bot from voice chat\n"
            help_msg += "!shuffle - Shuffles the queue\n"
            help_msg += "!move <songNumber> - Moves song at songNumber to the top\n"
            help_msg += "!loop <queue> - Loops song. Optional 'queue' loops queue. Use !loop twice to untoggle\n"
        elif message_content == "meme":
            help_msg += "Meme Commands\n"
            help_msg += "!memerboard <page# OR 'last'> - Display Meme Review leaderboard\n"
        else:
            help_msg += "What do you need help with?\n"
            help_msg += "!plshelp emote - Emote Leaderboard Commands\n"
            help_msg += "!plshelp music - Emote Leaderboard Commands\n"
            help_msg += "!plshelp meme - Meme Review Commands\n"
        await message.channel.send(help_msg)
    except Exception:
        await message.channel.send("Something went wrong... It's not your fault though, blame George.")

client.run(TOKEN)
