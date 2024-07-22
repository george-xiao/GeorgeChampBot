from datetime import datetime
import json
import os
import aiohttp
import discord
from dotenv import load_dotenv
import pytz

# Frequently used Objects
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
commandTree = discord.app_commands.CommandTree(client)
load_dotenv()
env = {
    "TOKEN": os.getenv("DISCORD_TOKEN"),
    "GUILD": os.getenv("DISCORD_GUILD"),
    "BOT_ID": os.getenv("BOT_ID"),
    "ADMIN_ROLE": os.getenv("ADMIN_ROLE"),
    "MAIN_CHANNEL": os.getenv("MAIN_CHANNEL"),
    "BOT_CHANNEL": os.getenv("BOT_CHANNEL"),
    "ANNOUNCEMENT_CHANNEL": os.getenv("ANNOUNCEMENT_CHANNEL"),
    "ANNOUNCEMENT_DAY": int(os.getenv("ANNOUNCEMENT_DAY")),
    "ANNOUNCEMENT_HOUR": int(os.getenv("ANNOUNCEMENT_HOUR")),
    "ANNOUNCEMENT_MIN": int(os.getenv("ANNOUNCEMENT_MIN")),
    "WELCOME_ROLE": os.getenv("WELCOME_ROLE"),
    "DOTA_CHANNEL": os.getenv("DOTA_CHANNEL"),
    "TWITCH_CLIENT_ID": os.getenv("TWITCH_CLIENT_ID"),
    "TWITCH_CLIENT_SECRET": os.getenv("TWITCH_CLIENT_SECRET"),
    "MEME_CHANNEL": os.getenv("MEME_CHANNEL"),
    "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
    "MOVIE_CHANNEL": os.getenv("MOVIE_CHANNEL"),
    "MOVIE_ROLE": os.getenv("MOVIE_ROLE"),
}
botObject = None
guildObject = None
mainChannel = None
botChannel = None
# Color for Embedded Messages
embed_colour = {"MOVIE_NIGHT": 0x4F4279, "ERROR": 0xED4337}
MOVIE_EVENT_NAME = "Movie Night"
DELETE_AFTER_SECONDS = 10 * 60
DELETE_AFTER_HOURS = 24 * 60 * 60


class DiscordEmbedBuilder:
    def __init__(self, thumbnail_url="", colour_=0, title_="", description_="", title_url=""):
        self.embed_msg = discord.Embed(title=title_, colour=colour_, description=description_, url=title_url, type="rich")
        self.embed_msg.set_thumbnail(url=thumbnail_url)

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
def init_utils():
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


# Get printable version of role that will ping role when sent as a message
# role_name is key for env as all role_names should be stored within the .env file
def get_role_str(role_name: str) -> str | None:
    if role_id := get_role(env[role_name]).id:
        return f"<@&{str(role_id)}>"
    return None


# Get member object given member_name. member_name can be their username or their id
def get_member(member_name):
    for guild_member in guildObject.members:
        if guild_member.name == member_name or str(guild_member.id) == member_name:
            return guild_member


# Get printable version of member_name that will ping member when sent as a message
# member_name can be string or an id
def get_member_str(member_name) -> str | None:
    if member_object := get_member(member_name):
        return f"<@{str(member_object.id)}>"
    return None


# Get movie night's ScheduledEvent object. Returns None if not found
# Ignores cached ScheduledEvents that have been completed or cancelled
def get_movie_event() -> discord.ScheduledEvent | None:
    for event in guildObject.scheduled_events:
        if event.name.startswith(MOVIE_EVENT_NAME) and (event.status is discord.EventStatus.scheduled or event.status is discord.EventStatus.active) :
            return event
    return None


# Get shareable link for movie night's ScheduledEvent
def get_movie_event_link() -> str | None:
    if event := get_movie_event():
        return "https://discord.com/events/" + str(event.guild_id) + "/" + str(event.id)
    return None


# Checks to see if movie night's ScheduledEvent exists
# Returns an embed if ScheduledEvent does not exist
def movie_event_not_present(is_command):
    if not get_movie_event():
        embed = discord.Embed(colour=embed_colour["ERROR"])
        embed.title = f'"{MOVIE_EVENT_NAME}" event does not exist!'
        if is_command:
            embed.description = f'A Discord Event named "{MOVIE_EVENT_NAME}" needs to exist for this command to work!'
            embed.description += f"\nPlease contact {get_role_str('ADMIN_ROLE')} so that they can create this event."
        else:
            embed.description = f'A Discord Event named "{MOVIE_EVENT_NAME}" needs to exist for movie night features to work as intended!'
            embed.description += "\nPicking host and movie will not work until this event is created."
        return embed
    return None


# Converts seconds to MM:SS
def seconds_to_time(seconds):
    mins = str(int(seconds // 60))
    if len(mins) == 1:
        mins = "0" + mins
    secs = str(int(seconds % 60))
    if len(secs) == 1:
        secs = "0" + secs
    return mins + ":" + secs


# Convert time to EDT/EST; Sample Output: May 27, 02:00 PM
def convert_to_ottawa_time(original_time: datetime) -> datetime:
    desired_timezone = pytz.timezone("US/Eastern")
    desired_format = "%b %d, %I:%M %p %Z"
    return original_time.astimezone(desired_timezone).strftime(desired_format)


# Send a message using channel object
async def send_message(channel, msg: str = "", embed: discord.Embed = None, delete_after: float = None):
    await channel.send(msg, embed=embed, delete_after=delete_after)


# Get list of arguments after the command. If strict is true, arg_list will return empty if the number of arguments
# is not exactly correct. If false, it will return all arguments.
def get_arg_list(message, expected_num_args: int, strict: bool):
    arg_list = message.content.split()
    # ignore command
    if strict:
        arg_list = arg_list[1 : expected_num_args + 1]
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


# Send non-blocking get request; Returns json
# Discord bot cannot be blocked in execution
# As such get request is turned async with this function
async def async_get_request(url: str, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json


# Send non-blocking post request; Returns json
# Discord bot cannot be blocked in execution
# As such post request is turned async with this function
async def async_post_request(url: str, body):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=body) as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json


# Exception handling for admin-only slash commands
# Preceded by the decorator:
#   @<command_name>.error
# Sends an embedded message back to requestor
async def handle_member_missing_role_error(interaction: discord.Interaction):
    embed = discord.Embed(colour=embed_colour["ERROR"])
    embed.title = "Request Denied!"
    embed.description = f"Admin access is required for this command. Please contact {get_role_str('ADMIN_ROLE')} for more information."
    await interaction.response.send_message(get_role_str("ADMIN_ROLE"), embed=embed, delete_after=DELETE_AFTER_HOURS)


# Exception handling for slash commands
# Handles generic error
async def handle_slash_command_error(interaction: discord, error):
    embed = discord.Embed(colour=embed_colour["ERROR"])
    embed.title = "Request Denied!"
    embed.description = f"{str(error)}. Please contact {get_role_str('ADMIN_ROLE')} for more information."
    await interaction.response.send_message(get_role_str("ADMIN_ROLE"), embed=embed, delete_after=DELETE_AFTER_HOURS)
