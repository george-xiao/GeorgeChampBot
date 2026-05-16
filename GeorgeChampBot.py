import asyncio
from datetime import datetime
import os
import discord
from common import utils as ut
from components import emoteLeaderboard, dotaReplay, musicPlayer, twitchAnnouncement, memeReview, movieNight
from commands import load_commands

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

        # Initialize slash commands
        if not ut.commandTree:
            ut.commandTree = discord.app_commands.CommandTree(ut.client)
            load_commands(ut.commandTree)
        ut.commandTree.copy_global_to(guild=ut.guildObject)
        await ut.commandTree.sync(guild=ut.guildObject)

        global instanceRunning
        if instanceRunning:
            await ut.send_react_msg("GeorgeChampBot restarted! Check terminal for more information.", "georgechamp")
        else:
            instanceRunning = True
            await ut.send_react_msg("GeorgeChampBot reporting for duty!", "georgechamp")
            while 1:
                """
                DEPRECATED!
                Utilizing a global while loop to handle asynchronous commands introduces various race conditions and timeout issues.
                Please use the AsyncTask class under common/asyncTask.py instead.
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
    try:
        if message.author == ut.client.user:
            return None

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


ut.client.run(ut.env["TOKEN"])
