
import discord
import json
import os

# Frequently used Objects
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
env = None
botObject = None
guildObject = None
mainChannel = None
botChannel = None

class DiscordEmbedBuilder:
    def __init__(self, thumbnail_url="", colour_=0, title_="", description_="", title_url=""):
        self.embed_msg = discord.Embed(
            title=title_,
            colour=colour_,
            description=description_,
            url=title_url,
            type="rich"
        )
        self.embed_msg.set_thumbnail(url = thumbnail_url)

    # Set the url for the embed, only accepts http, https or local storage
    def set_thumbnail(self, image_url: str):
        self.embed_msg.set_thumbnail(url=image_url)

    # Accepts hex value for colour of embed
    def set_colour(self, colour: int):
        self.embed_msg.colour = colour

    # Sets title of embed (only single line, no newlines)
    def set_title(self, title: str):
        self.embed_msg.title = title

    # Sets description of embed
    def set_description(self, description: str):
        self.embed_msg.description = description

    # Sets url for embed title
    def set_url(self, url: str):
        self.embed_msg.url = url

    # Sets image
    def set_image(self, image_url: str):
        self.embed_msg.set_image(url=image_url)


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
    
# Send a message using channel object
async def send_message(channel, msg: str, embedded_msg=None):
    if embedded_msg:
        await channel.send(msg, embed=embedded_msg)
    else:
        await channel.send(msg)

# Get list of arguments after the command. If strict is true, arg_list will return empty if the number of arguments
# is not exactly correct. If false, it will return all arguments.
def get_arg_list(message, expected_num_args: int, strict: bool):
    arg_list = message.content.split()
    # ignore command
    if strict:
        arg_list = arg_list[1:expected_num_args+1]
        if len(arg_list) != expected_num_args:
            return []
    else:
        arg_list = arg_list[1:]
        if len(arg_list) < expected_num_args:
            return []

    return arg_list

# Given author object and admin role string, check if author is an admin
def author_is_admin(author, admin_role: str):
    is_admin = False

    admin = get_role(admin_role)

    for author_role in author.roles:
        if author_role == admin:
            is_admin = True
    
    return is_admin

# Given a relative path to a json file (from the place which it is called)
# and the file path from which it is called (__file__), return the contents
def create_json(relative_file_path: str, file_being_called_from: str):
    dirname = os.path.dirname(file_being_called_from)
    filename = os.path.join(dirname, relative_file_path)
    file = open(filename)
    json_contents = json.load(file)
    file.close()
    return json_contents

# Send message and react to it with emote if emoji exists
async def send_react_msg(msg_content: str, emoji_name: str):
    msg = await mainChannel.send(msg_content, delete_after=21600)
    target_emoji = None
    for emoji in guildObject.emojis:
        if emoji_name in emoji.name:
            target_emoji = emoji
    if target_emoji:
        await msg.add_reaction(target_emoji.name + ":" + str(target_emoji.id))
