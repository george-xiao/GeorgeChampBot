from discord import FFmpegPCMAudio
import googleapiclient.discovery
from youtube_dl import YoutubeDL
from collections import deque
from datetime import datetime
from .utils import seconds_to_time
from . import utils as ut
from urllib.parse import parse_qs, urlparse
import isodate
import discord
import random

YDL_OPTIONS = {'format': 'bestaudio/best', 'default_search': 'auto', 'quiet': 'True', 'no_warnings': 'True','ignoreerrors': 'False', 'source_address': '0.0.0.0', 'nocheckcertificate': 'True', "noplaylist": 'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
MAX_SONGS = 2000

song_queue = deque([])
voice_connection = None
loop_queue = False
loop_song = False

class SongItem:
    def __init__(self, entry, requester):
        self.url = f'https://www.youtube.com/watch?v={entry["id"]}'
        self.song = None
        self.title = entry["snippet"]["title"]
        self.channel_title = entry["snippet"]["channelTitle"]
        self.requester = requester
        self.duration = int(isodate.parse_duration(entry["contentDetails"]["duration"]).total_seconds()) # in seconds
        self.start_time = None # in seconds

# Constantly checking if the next song in queue should be played
async def play_song():
    try:
        global song_queue
        # Play next song if bot is in vc, bot is not currently playing a song, and there are songs in the queue
        if not voice_connection or voice_connection.is_playing() or not voice_connection.is_connected() or voice_connection.is_paused() or not song_queue:
            return

        if not loop_song:
            song = song_queue.popleft()
            if loop_queue:
                song_queue.append(song)

        if not song_queue:
            return

        song = song_queue[0].song
        song_queue[0].start_time = datetime.now()
        voice_connection.play(FFmpegPCMAudio(song, **FFMPEG_OPTIONS))
        await now_playing(ut.botChannel, True)
    except Exception as e:
        await ut.botChannel.send('Error Playing Next Song: ' + str(e))

# Constantly processing urls into song_queue
async def process_song():
    try:
        global song_queue, voice_connection, loop_queue, loop_song
        if not ut.botObject.voice or not ut.botObject.voice.channel and voice_connection:
            voice_connection = None
            song_queue = deque([])
            loop_queue, loop_song = False, False

        if len(song_queue) <= 1 or song_queue[1].song is not None:
            return

        url = song_queue[1].url
        info = YoutubeDL(YDL_OPTIONS).extract_info(url, download=False)
        song_queue[1].song = info["formats"][0]["url"]
    except Exception as e:
        await ut.botChannel.send('Error Processing Song: ' + str(e))

# Returns list of SongItems given input
async def process_input(user_input, requester, channel):
    video_ids = []
    query = parse_qs(urlparse(user_input).query, keep_blank_values=True)
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = ut.env["YOUTUBE_API_KEY"])
    if "list" in query:
        playlist_id = query["list"][0]
        request = youtube.playlistItems().list(
            part = "contentDetails",
            playlistId = playlist_id,
            maxResults = 50
        )
        response = request.execute()

        while request is not None:
            response = request.execute()
            for item in response["items"]:
                video_ids.append(item["contentDetails"]["videoId"])
            request = youtube.playlistItems().list_next(request, response)
    elif "v" in query:
        video_ids.append(query["v"][0])
    else:
        request = youtube.search().list(
            part="id",
            maxResults=1,
            q=user_input
        )
        response = request.execute()
        if response["items"]:
            video_ids.append(response["items"][0]["id"]["videoId"])
    
    if not video_ids:
        await channel.send(f"{user_input} not found :/")
        return []

    song_items = []
    for i in range(len(video_ids)//50 + 1):
        start = i * 50
        end = min((i+1) * 50, len(video_ids))
        request = youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(video_ids[start:end]),
            maxResults = 50
        )
        
        while request is not None:
            response = request.execute()
            
            for item in response["items"]:
                song_items.append(SongItem(item, requester))
            request = youtube.playlistItems().list_next(request, response)

    return song_items

async def play(message, user_input):
    try:
        if not await is_valid_command(message):
            return False

        global voice_connection
        try:
            voice_connection = await message.author.voice.channel.connect()
        except discord.ClientException:
            pass
        
        # Need this when starting the queue. since first element is 'now_playing'
        global song_queue
        if not song_queue:
            song_queue.append(None)

        added_songs = await process_input(user_input, message.author, message.channel)
        added_songs = added_songs[:MAX_SONGS - len(song_queue)]
        song_queue += added_songs
        
        await message.channel.send(f"Adding {len(added_songs)} songs.")
    except Exception as e:
        await message.channel.send('Error Playing Song: ' + str(e))
    
async def queue(message, page_num):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        if not page_num:
            page_num = 0
        else:
            page_num = int(page_num) - 1

        if len(song_queue) <= 1:
            await message.channel.send("Queue is empty.")
            return

        embed = discord.Embed(title="Queue", description="", colour=discord.Colour.dark_grey())
        start = page_num * 10 + 1
        end = min(len(song_queue), (page_num+1) * 10 + 1)
        for i in range(start, end):
            embed.description += f"{i}) {song_queue[i].title}\n"
        embed.set_footer(text=f"Page {page_num+1}/{(len(song_queue) - 2 )//10+1}")
        
        if embed.description == "" or page_num < 0:
            await message.channel.send("Page number out of range...")
        else:
            await message.channel.send(embed=embed)
    except Exception as e:
        await message.channel.send('Error Printing Queue: ' + str(e))
    
async def now_playing(message, isValid = False):
    try:
        if not isValid and not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        channel = message
        if not isValid:
            channel = message.channel

        if not song_queue:
            await channel.send("No songs playing currently.")
            return
        
        duration_time = seconds_to_time(song_queue[0].duration)
        curr_time = seconds_to_time((datetime.now() - song_queue[0].start_time).total_seconds())
        
        embed = discord.Embed(title="Now Playing", description=song_queue[0].title, colour=discord.Colour.dark_grey())
        embed.set_footer(text=curr_time + "/" + duration_time)
        await channel.send(embed=embed)
    except Exception as e:
        await channel.send('Error Printing Now Playing: ' + str(e))
    
async def shuffle(message):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        global song_queue
        if len(song_queue) <= 1:
            await message.channel.send("Queue is empty.")
            return

        curr_song = song_queue.popleft()
        random.shuffle(song_queue)
        song_queue.appendleft(curr_song)
        await message.channel.send("Playlist Shuffled!")
    except Exception as e:
        await message.channel.send('Error Shuffling: ' + str(e))
    
async def move(message, move_from):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        global song_queue
        if len(song_queue) <= 1:
            await message.channel.send("Queue is empty.")
            return

        move_from = int(move_from)
        if move_from < 1 or move_from > len(song_queue)-1:
            await message.channel.send(f"Index has to be between {1} and {len(song_queue) - 1}.")
            return

        moved_song = song_queue[move_from]
        del song_queue[move_from]
        song_queue.insert(1, moved_song)
        await message.channel.send(f"Moved {moved_song.title} to the top of the queue!")
    except Exception as e:
        await message.channel.send('Error Moving Song: ' + str(e))

async def skip(message):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        voice_connection.stop()
        await message.channel.send("Song Skipped.")
    except Exception as e:
        await message.channel.send('Error Skipping: ' + str(e))

async def clear(message):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        global song_queue
        if len(song_queue) >= 1:
            song_queue = deque([song_queue[0]])
        else:
            song_queue = deque([])
        await message.channel.send("Queue Cleared.")
    except Exception as e:
        await message.channel.send('Error Clearing Queue: ' + str(e))

async def disconnect(message):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        await voice_connection.disconnect() 
        await message.channel.send("Bot Disconnected.")
    except Exception as e:
        await message.channel.send('Error Disconnecting: ' + str(e))

async def resume(message):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        if voice_connection.is_paused():
            voice_connection.resume()
            await message.channel.send('Bot Resumed.')
        else:
            await message.channel.send('Bot is not paused.')
    except Exception as e:
        await message.channel.send('Error Resuming: ' + str(e))

async def pause(message):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        if not voice_connection.is_paused():
            voice_connection.pause()
            await message.channel.send('Bot Paused.')
        else:
            await message.channel.send('Bot is already paused.')
    except Exception as e:
        await message.channel.send('Error Pausing: ' + str(e))

async def loop(message, message_content):
    try:
        if not await is_valid_command(message) or not await is_bot_connected(message):
            return False

        message_content = message_content.lower()
        global loop_song
        global loop_queue
        if message_content == "queue" and not loop_queue:
            loop_queue = True
            loop_song = False
            await message.channel.send('Looped Queue.')
        elif message_content == "queue" and loop_queue:
            loop_queue = False
            await message.channel.send('Unlooped Queue.')
        elif not loop_song:
            loop_song = True
            loop_queue = False
            await message.channel.send('Looped Song.')
        else:
            loop_song = False
            await message.channel.send('Unlooped Song.')
    except Exception as e:
        await message.channel.send('Error Looping: ' + str(e))

async def is_valid_command(message):
    try:
        if message.channel != ut.botChannel:
            await message.channel.send(f"Music Commands should only be in '{ut.botChannel.name}'", delete_after=300)
        elif not message.author.voice or not message.author.voice.channel:
            await message.channel.send('Please enter a voice channel')
        elif voice_connection and ut.botObject.voice.channel != message.author.voice.channel:
            await message.channel.send('Please enter the same voice channel as the bot')
        else:
            return True

        return False
    except Exception as e:
        await message.channel.send('Error Validating Music Command: ' + str(e))

async def is_bot_connected(message):
    if not voice_connection:
        await message.channel.send('Bot is not playing music currently')
        return False
    return True