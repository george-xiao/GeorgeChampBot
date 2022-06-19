import asyncio
from datetime import datetime
import discord
from common.utils import *
from common import utils as ut
from dotenv import load_dotenv
import os
import inspect

from components import emoteLeaderboard, dotaReplay, music, twitchAnnouncement, memeReview


load_dotenv()
# TODO: Make these Ids not hardcoded
PLAYER_1_ID = os.getenv('PLAYER_1_ID')
PLAYER_2_ID = os.getenv('PLAYER_2_ID')
PLAYER_3_ID = os.getenv('PLAYER_3_ID')
PLAYER_4_ID = os.getenv('PLAYER_4_ID')
TWITCH_USER_1 = os.getenv('TWITCH_USER_1')
TWITCH_USER_2 = os.getenv('TWITCH_USER_2')
env = {
"TOKEN": os.getenv('DISCORD_TOKEN'),
"GUILD": os.getenv('DISCORD_GUILD'),
"BOT_ID": os.getenv('BOT_ID'),
"ADMIN_ROLE": os.getenv('ADMIN_ROLE'),
"MAIN_CHANNEL": os.getenv('MAIN_CHANNEL'),
"BOT_CHANNEL": os.getenv('BOT_CHANNEL'),
"ANNOUNCEMENT_CHANNEL": os.getenv('ANNOUNCEMENT_CHANNEL'),
"ANNOUNCEMENT_DAY": int(os.getenv('ANNOUNCEMENT_DAY')),
"ANNOUNCEMENT_HOUR": int(os.getenv('ANNOUNCEMENT_HOUR')),
"ANNOUNCEMENT_MIN": int(os.getenv('ANNOUNCEMENT_MIN')),
"WELCOME_ROLE": os.getenv("WELCOME_ROLE"),
"OPENDOTA_API_KEY": os.getenv('OPENDOTA_API_KEY'),
"DOTA_CHANNEL": os.getenv("DOTA_CHANNEL"),
"player_list": [PLAYER_1_ID, PLAYER_2_ID, PLAYER_3_ID, PLAYER_4_ID],
"TWITCH_OAUTH_TOKEN": os.getenv('TWITCH_OAUTH_TOKEN'),
"TWITCH_CLIENT_ID": os.getenv('TWITCH_CLIENT_ID'),
"twitch_user_list": [TWITCH_USER_1, TWITCH_USER_2],
"twitch_curr_live": [],
"MEME_CHANNEL": os.getenv('MEME_CHANNEL'),
"YOUTUBE_API_KEY": os.getenv('YOUTUBE_API_KEY')
}

prev_hour = False
api_running = False

@ut.client.event
async def on_ready():
    init_utils(env)

    georgechamp_emoji = None
    for emoji in ut.guildObject.emojis:
        if 'georgechamp' in emoji.name:
            georgechamp_emoji = emoji

    msg = await ut.mainChannel.send("GeorgeChampBot reporting for duty!", delete_after=21600)
    try:
        await msg.add_reaction(georgechamp_emoji.name + ":" + str(georgechamp_emoji.id))
    except:
        pass

    if not(os.path.exists("database")):
        try:
            os.mkdir("./database")
        except:
            await ut.mainChannel.send("Error creating Database.")

    global api_running
    global prev_hour
    if api_running is False:
        
        a_channel = get_channel(env["ANNOUNCEMENT_CHANNEL"])
        
        while 1:
            api_running = True
            curr_date = datetime.now()
            
            announceDay = env["ANNOUNCEMENT_DAY"]
            announceHour = env["ANNOUNCEMENT_HOUR"]
            announceMinute = env["ANNOUNCEMENT_MIN"]

            if (curr_date.second % 55) == 0:
                await twitchAnnouncement.check_twitch_live(ut.mainChannel)
                if curr_date.weekday() == announceDay and curr_date.hour == announceHour and curr_date.minute == announceMinute:
                    await emoteLeaderboard.announcement_task(a_channel, 604800)
                    await emoteLeaderboard.announcement_task(ut.mainChannel)
                if curr_date.weekday() == ((announceDay-1)%7) and curr_date.hour == announceHour and curr_date.minute == announceMinute:
                    await memeReview.best_announcement_task(a_channel, 604800)
                    await memeReview.best_announcement_task(ut.mainChannel)
                if curr_date.hour == 00 and curr_date.minute == 00:
                    await memeReview.resetLimit()
                # what min of hour should u check; prints only if the current games have not been printed
                if (prev_hour != curr_date.hour and curr_date.minute == 00):
                    d_channel = get_channel(env["DOTA_CHANNEL"])
                    prev_hour = curr_date.hour
                    try:
                        await dotaReplay.check_recent_matches(d_channel)
                    except:
                        api_running = False

            if (curr_date.second % 1) == 0:
                await music.play_song()

            await asyncio.sleep(1)


@ut.client.event
async def on_member_join(member):
    try:
        await ut.mainChannel.send("Welcome <@" + str(member.id) + "> to a wholesome server!")
        role = get_role(env["WELCOME_ROLE"])
        await member.add_roles(discord.utils.get(member.guild.roles, name=role.name))
    except Exception as e:
        await ut.mainChannel.send('There was an error running this command ' + str(e))  # if error


@ut.client.event
async def on_member_remove(member):
    await ut.mainChannel.send(member.name + " has decided to leave us :(")


#@ut.client.event
async def on_disconnect():
   try:
        await music.disconnect()
    #    await ut.mainChannel.send("GeorgeChampBot signing out!")
   except Exception:
       await ut.mainChannel.send("I believe I am leaving but something went wrong... Blame George.")


@ut.client.event
async def on_message(message):
    if message.author == ut.client.user:
        return None
    
    command_name = " ".join(message.content.lower().split()[:1])
    message_content = " ".join(message.content.split()[1:])

    if command_name in ['!p', '!play']:
        await music.play(message, message_content)
    elif command_name in ['!pause']:
        await music.pause(message)
    elif command_name in ['!resume']:
        await music.resume(message)
    elif command_name in ['!queue']:
        await music.queue(message, message_content)
    elif command_name in ['!nowplaying', '!np']:
        await music.now_playing(message)
    elif command_name in ['!skip', '!next']:
        await music.skip(message, message_content)
    elif command_name in ['!clear']:
        await music.clear(message)
    elif command_name in ['!disconnect']:
        await music.disconnect(message)
    elif command_name in ['!shuffle']:
        await music.shuffle(message)
    elif command_name in ['!move']:
        await music.move(message, message_content)
    elif command_name in ['!loop']:
        await music.loop(message)
    elif command_name in ['!plshelp']:
        await print_help(message, message_content)
    elif command_name in ['!plscount']:
        await emoteLeaderboard.print_count(message)
    elif command_name in ['!leaderboard']:
        await emoteLeaderboard.print_leaderboard(message)
    elif command_name in ['!memerboard']:
        await memeReview.print_memerboard(message)
    elif command_name in ['!plstransfer']:
        await emoteLeaderboard.pls_transfer(message, get_role(env["ADMIN_ROLE"]))
    elif command_name in ['!plsdelete']:
        await emoteLeaderboard.pls_delete(message, get_role(env["ADMIN_ROLE"]))
    elif command_name in ['!plsadd-dota']:
        await dotaReplay.add_player(message, env["ADMIN_ROLE"])
    elif command_name in ['!plsremove-dota']:
        await dotaReplay.remove_player(message, env["ADMIN_ROLE"])
    elif command_name in ['!plslist-dota']:
        await dotaReplay.list_players(message.channel)
    else:
        await memeReview.check_meme(message, ut.guildObject, ut.mainChannel, get_channel(env["MEME_CHANNEL"]))
        await emoteLeaderboard.check_emoji(message, ut.guildObject)


@ut.client.event
async def on_raw_reaction_add(payload):
    is_meme = await memeReview.add_meme_reactions(payload, get_channel(env["MEME_CHANNEL"]), ut.guildObject, get_role(env["ADMIN_ROLE"]))
    if not is_meme:
        await emoteLeaderboard.check_reaction(payload, ut.guildObject, ut.mainChannel)
    
@ut.client.event
async def on_raw_reaction_remove(payload):
    await memeReview.remove_meme_reactions(payload, get_channel(env["MEME_CHANNEL"]))

@ut.client.event
async def on_guild_emojis_update(guild, before, after):
    await emoteLeaderboard.rename_emote(ut.mainChannel,before,after)

async def print_help(message, message_content):
    try:
        message_content = message_content.lower()
        help_msg = ""
        embed = ut.DiscordEmbedBuilder()
        if message_content == "emote":
            description = inspect.cleandoc("""
                !plscount <emote> - All time score of <emote>
                !leaderboard <page# OR 'last'> - All time emoji scores
                !plstransfer <emoteFrom> -> <emoteTo> - Transfers emoteFrom to emoteTo (Admin Only)
                !plsdelete <emote> - Deletes emote from database (Admin Only)""")
            embed = ut.DiscordEmbedBuilder(colour_ = 0xFFDE34, title_ = "Emote Leaderboard Commands", description_ = description, thumbnail_url = "https://cdn.discordapp.com/emojis/815268205010485318.webp?size=96&quality=lossless")
        elif message_content == "music":
            description = inspect.cleandoc("""
                !p <song> - Plays songs or playlists
                !pause - Pauses the song
                !resume - Resumes the song
                !skip <song#> - Skips song. song# specifies index.
                !np - Currently playing song
                !queue <page#> - Prints queue
                !clear - Clears the queue
                !disconnect - Disconnects bot from voice chat
                !shuffle - Shuffles the queue
                !move <song#> - Moves song at songNumber to the top
                !loop - Loops Queue -> Loops Song -> Disables Loop """)
            embed = ut.DiscordEmbedBuilder(colour_ = 0xFF0000, title_ = "Music Player Commands", description_ = description, thumbnail_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTf4296-YNIH5GmtQznpe_qgBsLxCtQZBgUtg&usqp=CAU")
        elif message_content == "meme":
            description = inspect.cleandoc("""
                !memerboard <page# OR 'last'> - Display Meme Review leaderboard""")
            embed = ut.DiscordEmbedBuilder(colour_ = 0x000000, title_ = "Meme Commands", description_ = description, thumbnail_url = "https://cdn.discordapp.com/emojis/667584569444270080.webp?size=96&quality=lossless")
        elif message_content == "dota":
            description = inspect.cleandoc("""
                !plsadd-dota <Name> <Player ID> - Add player to tracking list (Admin Only)
                !plsremove-dota <Name or Player ID> - Remove player from tracking list (Admin Only)
                !plslist-dota - List currently tracked players""")
            embed = ut.DiscordEmbedBuilder(colour_ = 0x0047AB, title_ = "Dota Commands", description_ = description, thumbnail_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQp8emc_vN_kjb7616lE0JMIp9Igeko58cd1g&usqp=CAU")
        else:
            description = inspect.cleandoc("""
                !plshelp emote - Emote Leaderboard Commands
                !plshelp music - Music Leaderboard Commands
                !plshelp meme - Meme Review Commands
                !plshelp dota - Dota Commands""")
            embed = ut.DiscordEmbedBuilder(colour_ = 0x4F7942, title_ = "What do you need help with?", description_ = description, thumbnail_url = "https://ih1.redbubble.net/image.3510672545.8841/st,small,507x507-pad,600x600,f8f8f8.jpg")
        await ut.send_message(message.channel, "", embed.embed_msg)
    except Exception:
        await message.channel.send("Something went wrong... It's not your fault though, blame George.")

ut.client.run(env["TOKEN"])
