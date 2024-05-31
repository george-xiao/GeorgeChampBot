import asyncio
from datetime import datetime
import os
import inspect
import discord
from common import utils as ut
from components import emoteLeaderboard, dotaReplay, musicPlayer, twitchAnnouncement, memeReview, movieNight

# Ensures that only one for loop is running per application
# Bypasses bug where on_ready() is called every time bot comes up after after connection lost
instanceRunning = False


@ut.client.event
async def on_ready():
    try:
        ut.init_utils()
        if not os.path.exists("database"):
            os.mkdir("database")
        await emoteLeaderboard.init_emote_leaderboard()
        musicPlayer.reset_state()
        movieNight.init()
        ut.commandTree.add_command(movieNight.movie_night_group, guild=ut.guildObject)

        global instanceRunning
        if instanceRunning:
            await ut.send_react_msg("GeorgeChampBot restarted! Check terminal for more information.", "georgechamp")
        else:
            instanceRunning = True
            await ut.send_react_msg("GeorgeChampBot reporting for duty!", "georgechamp")
            while 1:
                """
                DEPRECATED!
                Utilizing a global while loop to handle asynchronous commands introduces various race condtions and timeout issues.
                Please use the AsyncTask ckass under common/asyncTask.py instead.
                TODO: Refactor existing statements within this while loop to use AsyncTask instead.
                """
                curr_date = datetime.now()

                announceDay = ut.env["ANNOUNCEMENT_DAY"]
                announceHour = ut.env["ANNOUNCEMENT_HOUR"]
                announceMinute = ut.env["ANNOUNCEMENT_MIN"]

                # Announcements
                if curr_date.weekday() == announceDay and curr_date.hour == announceHour and curr_date.minute == announceMinute and curr_date.second == 0:
                    await emoteLeaderboard.announcement_task()
                if curr_date.weekday() == ((announceDay - 1) % 7) and curr_date.hour == announceHour and curr_date.minute == announceMinute and curr_date.second == 0:
                    await memeReview.best_announcement_task(ut.mainChannel)

                # every 24 hours
                if (curr_date.hour % 24 == 0) and curr_date.minute == 0 and curr_date.second == 0:
                    await memeReview.resetLimit()

                # every 1 hour
                if (curr_date.hour % 1 == 0) and curr_date.minute == 0 and curr_date.second == 0:
                    await dotaReplay.check_recent_matches(ut.get_channel(ut.env["DOTA_CHANNEL"]))

                # every 15 minute
                if (curr_date.minute % 15) == 0 and curr_date.second == 0:
                    await twitchAnnouncement.check_twitch_live(ut.mainChannel)

                # every 3 minutes
                if (curr_date.minute % 3) == 0 and curr_date.second == 0:
                    await musicPlayer.check_disconnect()

                # every 1 second
                if (curr_date.second % 1) == 0:
                    await musicPlayer.play_song()

                await asyncio.sleep(1)
    except Exception as e:
        await ut.mainChannel.send("Error With On Ready Event: " + str(e))


@ut.client.event
async def on_member_join(member):
    try:
        await ut.mainChannel.send("Welcome <@" + str(member.id) + "> to a wholesome server!")
        role = ut.get_role(ut.env["WELCOME_ROLE"])
        await member.add_roles(discord.utils.get(member.guild.roles, name=role.name))
    except Exception as e:
        await ut.mainChannel.send("Error With On Member Join Event: " + str(e))


@ut.client.event
async def on_member_remove(member):
    try:
        await ut.mainChannel.send(member.name + " has decided to leave us :(")
    except Exception as e:
        await ut.mainChannel.send("Error With On Ready Event: " + str(e))


@ut.client.event
async def on_message(message):
    """
    DEPRECATED!
    Please use slash commands instead as it is more powerful and provides seamless integration with Discord.
    Documentation: https://discordpy.readthedocs.io/en/stable/interactions/api.html#application-commands
    TODO: Refactor existing commands to use slash commands instead.
    """
    try:
        if message.author == ut.client.user:
            return None

        command_name = " ".join(message.content.lower().split()[:1])
        message_content = " ".join(message.content.split()[1:])

        if command_name in ["!plshelp"]:
            await print_help(message, message_content)
        # Music Player commands
        elif command_name in ["!p", "!play"]:
            await musicPlayer.play(message, message_content)
        elif command_name in ["!pause", "!resume", "!stop"]:
            await musicPlayer.pause(message)
        elif command_name in ["!queue"]:
            await musicPlayer.queue(message, message_content)
        elif command_name in ["!nowplaying", "!np"]:
            await musicPlayer.now_playing(message)
        elif command_name in ["!skip", "!next"]:
            await musicPlayer.skip(message, message_content)
        elif command_name in ["!clear"]:
            await musicPlayer.clear(message)
        elif command_name in ["!disconnect"]:
            await musicPlayer.disconnect(message)
        elif command_name in ["!shuffle"]:
            await musicPlayer.shuffle(message)
        elif command_name in ["!move"]:
            await musicPlayer.move(message, message_content)
        elif command_name in ["!loop"]:
            await musicPlayer.loop(message)
        # Emote Leaderboard commands
        elif command_name in ["!plscount"]:
            await emoteLeaderboard.print_count(message, message_content)
        elif command_name in ["!leaderboard"]:
            await emoteLeaderboard.print_leaderboard(message, message_content)
        elif command_name in ["!plstransfer"]:
            await emoteLeaderboard.pls_transfer(message, message_content, ut.env["ADMIN_ROLE"])
        elif command_name in ["!plsdelete"]:
            await emoteLeaderboard.pls_delete(message, message_content, ut.env["ADMIN_ROLE"])
        elif command_name in ["!plsaddscore_h"]:
            await emoteLeaderboard.plsaddscore_h(message, message_content, ut.env["ADMIN_ROLE"])
        # Meme Review commands
        elif command_name in ["!memerboard"]:
            await memeReview.print_memerboard(message)
        # Dota Replay commands
        elif command_name in ["!plsadd-dota"]:
            await dotaReplay.add_player(message, ut.env["ADMIN_ROLE"])
        elif command_name in ["!plsremove-dota"]:
            await dotaReplay.remove_player(message, ut.env["ADMIN_ROLE"])
        elif command_name in ["!plslist-dota"]:
            await dotaReplay.list_players(message.channel)
        elif command_name in ["!plsadd-twitch"]:
            await twitchAnnouncement.add_streamer(message, ut.env["ADMIN_ROLE"])
        elif command_name in ["!plsremove-twitch"]:
            await twitchAnnouncement.remove_streamer(message, ut.env["ADMIN_ROLE"])
        elif command_name in ["!plslist-twitch"]:
            await twitchAnnouncement.list_streamers(message.channel)
        elif command_name in ["!plssync"]:
            channel = message.channel
            if not ut.author_is_admin(message.author, ut.env["ADMIN_ROLE"]):
                await ut.send_message(channel, "Sorry, you need to be a dictator to use this command.")
                return
            ut.commandTree.copy_global_to(guild=ut.guildObject)
            result = await ut.commandTree.sync(guild=ut.guildObject)
            await ut.send_message(channel, "Commands Synced: " + " ".join(command.name for command in result))
        else:
            await memeReview.check_meme(message, ut.guildObject, ut.mainChannel, ut.get_channel(ut.env["MEME_CHANNEL"]))
            await emoteLeaderboard.check_emoji(message)
    except Exception as e:
        await ut.mainChannel.send("Error With On Message Event: " + str(e))


@ut.client.event
async def on_raw_reaction_add(payload):
    try:
        is_meme = await memeReview.add_meme_reactions(payload, ut.get_channel(ut.env["MEME_CHANNEL"]), ut.guildObject, ut.get_role(ut.env["ADMIN_ROLE"]))
        if not is_meme:
            await emoteLeaderboard.check_reaction(payload)
    except Exception as e:
        await ut.mainChannel.send("Error With On Reaction Add Event: " + str(e))


@ut.client.event
async def on_raw_reaction_remove(payload):
    try:
        await memeReview.remove_meme_reactions(payload, ut.get_channel(ut.env["MEME_CHANNEL"]))
    except Exception as e:
        await ut.mainChannel.send("Error With On Reaction Remove Event: " + str(e))


@ut.client.event
async def on_guild_emojis_update(_guild, before, after):
    try:
        await emoteLeaderboard.rename_emote(before, after)
    except Exception as e:
        await ut.mainChannel.send("Error With On Emoji Update Event: " + str(e))


@ut.client.event
async def on_voice_state_update(member, before, after):
    try:
        # When Bot Disconnects
        if member == ut.botObject and before.channel is not None and after.channel is None:
            musicPlayer.reset_state()
    except Exception as e:
        await ut.mainChannel.send("Error With On Voice State Update Event: " + str(e))


async def print_help(message, message_content):
    """
    DEPRECATED!
    Please use slash commands instead as it is more powerful and provides seamless integration with Discord.
    Documentation: https://discordpy.readthedocs.io/en/stable/interactions/api.html#application-commands
    TODO: Refactor existing commands to use slash commands instead.
    """
    message_content = message_content.lower()
    embed = ut.DiscordEmbedBuilder()
    if message_content == "hidden":
        description = inspect.cleandoc(
            """
            !plsaddscore_h <emote> <score> - Manually adds <score> to <emote>
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0xFFDE34, title_="Emote Leaderboard Commands", description_=description, thumbnail_url="https://cdn.discordapp.com/emojis/815268205010485318.webp?size=96&quality=lossless")
    elif message_content == "emote":
        description = inspect.cleandoc(
            """
            !plscount <emote> - All time score of <emote>
            !leaderboard <page# OR 'last'> - All time emoji scores. -u shows deleted emotes.
            !plstransfer <emoteFrom> <emoteTo> - Transfers emoteFrom to emoteTo (Admin Only)
            !plsdelete <emote> - Deletes emote from database (Admin Only)
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0xFFDE34, title_="Emote Leaderboard Commands", description_=description, thumbnail_url="https://cdn.discordapp.com/emojis/815268205010485318.webp?size=96&quality=lossless")
    elif message_content == "music":
        description = inspect.cleandoc(
            """
            !p <song> - Plays songs or playlists
            !pause - Cycles through: Pause -> Resume
            !skip <song#> - Skips song at song#. Defaults to current song
            !np - Currently playing song
            !queue <page#> - Prints queue. Default page# - 1
            !clear - Clears the queue
            !disconnect - Disconnects bot from voice chat
            !shuffle - Shuffles the queue
            !move <moveFrom> <moveTo> - Moves song from moveFrom to moveTo. Default moveTo = 1
            !loop - Cycles through: Loop Queue -> Loop Song -> Disable Loop 
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0xFF0000, title_="Music Player Commands", description_=description, thumbnail_url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTf4296-YNIH5GmtQznpe_qgBsLxCtQZBgUtg&usqp=CAU")
    elif message_content == "meme":
        description = inspect.cleandoc(
            """
            memerboard <page# OR 'last'> - Display Meme Review leaderboard
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0x000000, title_="Meme Commands", description_=description, thumbnail_url="https://cdn.discordapp.com/emojis/667584569444270080.webp?size=96&quality=lossless")
    elif message_content == "dota":
        description = inspect.cleandoc(
            """
            !plsadd-dota <Name> <Player ID> - Add player to tracking list (Admin Only)
            !plsremove-dota <Name or Player ID> - Remove player from tracking list (Admin Only)
            !plslist-dota - List currently tracked players
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0x0047AB, title_="Dota Commands", description_=description, thumbnail_url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQp8emc_vN_kjb7616lE0JMIp9Igeko58cd1g&usqp=CAU")
    elif message_content == "twitch":
        description = inspect.cleandoc(
            """
            !plsadd-twitch <Name> <Twitch Username> - Add streamer to tracking list (Admin Only)
            !plsremove-twitch <Name or Twitch Username> - Remove streamer from tracking list (Admin Only)
            !plslist-twitch - List currently tracked twitch streamers
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0x0047AB, title_="Twitch Commands", description_=description, thumbnail_url="https://brand.twitch.tv/assets/images/black.png")
    else:
        description = inspect.cleandoc(
            """
            !plshelp emote - Emote Leaderboard Commands
            !plshelp music - Music Leaderboard Commands
            !plshelp meme - Meme Review Commands
            !plshelp dota - Dota Commands
            !plshelp twitch - Twitch Commands
            """
        )
        embed = ut.DiscordEmbedBuilder(colour_=0x4F7942, title_="What do you need help with?", description_=description, thumbnail_url="https://ih1.redbubble.net/image.3510672545.8841/st,small,507x507-pad,600x600,f8f8f8.jpg")
    await ut.send_message(message.channel, embed=embed.embed_msg)


ut.client.run(ut.env["TOKEN"])
