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

        # Start periodic tasks
        movieNight.init()
        emoteLeaderboard.init()
        memeReview.init()
        dotaReplay.init()
        twitchAnnouncement.init()
        musicPlayer.init()

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
        await ut.mainChannel.send("Error With On Member Remove Event: " + str(e))


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
        is_meme = await memeReview.add_meme_reactions(
            payload, ut.get_channel(ut.env["MEME_CHANNEL"]), ut.guildObject, ut.get_role(ut.env["ADMIN_ROLE"])
        )
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


if __name__ == "__main__":
    ut.client.run(ut.env["TOKEN"])
