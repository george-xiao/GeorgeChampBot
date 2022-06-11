
import discord

# Frequently used Objects
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
env = None
botObject = None
guildObject = None
mainChannel = None
botChannel = None

# initialize the constants
def init_utils(_env):
    global env
    env = _env

    global guildObject
    for guild in client.guilds:
        if guild.name == env["GUILD"]:
            guildObject = guild

    global mainChannel
    mainChannel = get_channel(env["MAIN_CHANNEL"])

    global botChannel
    botChannel = get_channel(env["BOT_CHANNEL"])

    global botObject
    botObject = get_member(env["BOT_ID"])

# Get channel object given channel_name. channel_name can also be an id
def get_channel(channel_name):
    for guild_channel in guildObject.channels:
        if guild_channel.name == channel_name or str(guild_channel.id) == channel_name:
            return guild_channel

# Get role object.
def get_role(role_name):
    for role in guildObject.roles:
        role_name_list = [role_name]
        if role_name[0] == "@":
            role_name_list.append(role_name[1:])
        else:
            role_name_list.append("@" + role_name)
        if role.name in role_name_list:
            return role

# Get member object given member_name. member_name can also be an id
def get_member(member_name):
    for guild_member in guildObject.members:
        if guild_member.name == member_name or str(guild_member.id) == member_name:
            return guild_member

# Converts seconds to MM:SS
def seconds_to_time(seconds):
    mins = str(int(seconds // 60))
    if len(mins) == 1:
        mins = "0" + mins
    secs = str(int(seconds % 60))
    if len(secs) == 1:
        secs = "0" + secs
    return mins + ":" + secs