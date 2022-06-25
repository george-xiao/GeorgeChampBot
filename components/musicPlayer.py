import asyncio
from discord import FFmpegPCMAudio
import googleapiclient.discovery
from youtube_dl import YoutubeDL
from collections import deque
from datetime import datetime
import sys
sys.path.insert(1, '../common')
import common.utils as ut
from urllib.parse import parse_qs, urlparse
import isodate
import discord
import random
from math import ceil

YDL_OPTIONS = {'format': 'bestaudio/best', 'default_search': 'auto', 'quiet': 'True', 'no_warnings': 'True','ignoreerrors': 'False', 'source_address': '0.0.0.0', 'nocheckcertificate': 'True', "noplaylist": 'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
MAX_SONGS = 1500
MAX_DISCONNECT_TIME = 180
LOOPDISABLED = "LOOPDISABLED"
LOOPQUEUE = "LOOPQUEUE"
LOOPSONG = "LOOPSONG"


class SongItem:
    def __init__(self, entry, requester):
        self.yt_url = f'https://www.youtube.com/watch?v={entry["id"]}'
        self.song_url = None
        self.title = entry["snippet"]["title"]
        self.channel_title = entry["snippet"]["channelTitle"]
        self.requester = requester
        self.duration = int(isodate.parse_duration(entry["contentDetails"]["duration"]).total_seconds()) # in seconds
        self.start_time = None # in seconds
        
class SongQueue:
    def __init__(self):
        self.curr_song = None
        self.queue = deque([])

# RESET GLOBALS IN DISCONNECT
sq = SongQueue()
vc = None
loop_status = LOOPDISABLED
invalid_start = datetime.now()

# Constantly checking if the next song in queue should be played
async def play_song():
    try:
        global sq
        if not await process_song(sq):
            return

        if not vc or vc.is_playing() or not vc.is_connected() or vc.is_paused() or (not sq.queue and not sq.curr_song):
            # if bot disconnected from voice channel, ensure state is reset (in case someone disconnects using discord ui)
            if vc and not vc.is_connected():
                await disconnect(ut.botChannel, is_bot=True)
            # disconnect if no songs playing or no members in voice channel
            if not (vc and (not sq.curr_song or (len(vc.channel.members) == 1))):
                global invalid_start
                invalid_start = datetime.now()
            elif (datetime.now() - invalid_start).total_seconds() >= MAX_DISCONNECT_TIME:
                await disconnect(ut.botChannel, is_bot=True)
            return

        # if queue is empty, nothing left to play
        if not sq.queue and sq.curr_song:
            sq.curr_song = None
            return

        if (loop_status == LOOPQUEUE):
            sq.queue.append(sq.curr_song)
        if not (loop_status == LOOPSONG):
            sq.curr_song = sq.queue.popleft()

        sq.curr_song.start_time = datetime.now()
        vc.play(FFmpegPCMAudio(sq.curr_song.song_url, **FFMPEG_OPTIONS))
        await now_playing(ut.botChannel, delete_after=sq.curr_song.duration, is_bot=True)
    except Exception as e:
        await ut.botChannel.send('Error Playing Next Song: ' + str(e))

# Constantly processing urls into sq
async def process_song(sq):
    if not sq.queue or sq.queue[0].song_url is not None:
        return True
    next_song = sq.queue[0]
    info = YoutubeDL(YDL_OPTIONS).extract_info(next_song.yt_url, download=False)
    if not info:
        await ut.botChannel.send(f'Removed {next_song.title} ({next_song.yt_url}). Song is inappropriate or unavailable')
        sq.queue.popleft()
        return False
    next_song.song_url = info["formats"][0]["url"]
    return True

# Returns list of SongItems given input
async def process_input(user_input, requester):
    video_ids = []
    query = parse_qs(urlparse(user_input).query, keep_blank_values=True)
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey = ut.env["YOUTUBE_API_KEY"])
    if not query:
        request = youtube.search().list(
            part="id",
            maxResults=1,
            q=user_input
        )
        response = request.execute()
        if response["items"] and "videoId" in response["items"][0]["id"]:
            video_ids.append(response["items"][0]["id"]["videoId"])
    elif "youtube.com/watch" in user_input:
        video_ids.append(query["v"][0])
    if "youtube.com/playlist" in user_input:
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
            if len(video_ids) > MAX_SONGS+1:
                break
    
    if not video_ids:
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

        global vc
        if vc is None:
            vc = await message.author.voice.channel.connect()
        
        global sq
        processed_songs = await process_input(user_input, message.author)
        added_songs = processed_songs[:MAX_SONGS - len(sq.queue)]
        sq.queue += added_songs
        
        if len(processed_songs) != len(added_songs):
            await message.channel.send(f"{MAX_SONGS} song limit reached!")
        if len(processed_songs) == 0:
            await message.channel.send(f"Couldn't find '{user_input}'")
        elif len(added_songs) == 1:
            await message.channel.send(f"Added '{added_songs[0].title}' at position {len(sq.queue)}")
        else:
            await message.channel.send(f"Added {len(added_songs)} songs.")
    except Exception as e:
        await message.channel.send('Error Playing Song: ' + str(e))
    
async def queue(message, page_num):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        if not page_num:
            page_num = 0
        else:
            page_num = int(page_num) - 1

        if not len(sq.queue):
            await message.channel.send("Queue is empty.")
            return

        embed = discord.Embed(title="Queue", description="", colour=discord.Colour.dark_grey())
        start = page_num * 10
        end = min(len(sq.queue), (page_num+1) * 10)
        for i in range(start, end):
            embed.description += f"{i+1}) {sq.queue[i].title}\n"
        embed.set_footer(text=f"Page {page_num+1}/{ceil(len(sq.queue)/10)}")
        
        if embed.description == "" or page_num < 0:
            await message.channel.send("Page number out of range...")
        else:
            await message.channel.send(embed=embed)
    except Exception as e:
        await message.channel.send('Error Printing Queue: ' + str(e))
    
async def now_playing(message, is_bot = False, delete_after=None):
    try:
        if not is_bot and not await is_valid_command(message, check_bot_connected = False):
            return False

        channel = message
        if not is_bot:
            channel = channel.channel

        if not sq.curr_song:
            await channel.send("No songs playing currently.")
            return
        
        song = sq.curr_song

        duration_time = ut.seconds_to_time(song.duration)
        curr_time = ut.seconds_to_time((datetime.now() - song.start_time).total_seconds())
        
        embed = discord.Embed(title="Now Playing", description=song.title, colour=discord.Colour.dark_grey())
        embed.set_footer(text=curr_time + "/" + duration_time)
        await channel.send(embed=embed, delete_after=delete_after)
    except Exception as e:
        await channel.send('Error Printing Now Playing: ' + str(e))
    
async def shuffle(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global sq
        if not sq.queue:
            await message.channel.send("Queue is empty.")
            return

        random.shuffle(sq.queue)
        await message.channel.send("Playlist Shuffled!")
    except Exception as e:
        await message.channel.send('Error Shuffling: ' + str(e))
    
async def move(message, move_from):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global sq
        if not sq.queue:
            await message.channel.send("Queue is empty.")
            return

        move_from = int(move_from) - 1
        if move_from < 0 or move_from >= len(sq.queue):
            await message.channel.send(f"Index has to be between {1} and {len(sq.queue)}.")
            return

        moved_song = sq.queue[move_from]
        del sq.queue[move_from]
        sq.queue.appendleft(moved_song)
        await message.channel.send(f"Moved '{moved_song.title}' to the top of the queue!")
    except Exception as e:
        await message.channel.send('Error Moving Song: ' + str(e))

async def skip(message, skip_idx):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global sq
        if not skip_idx:
            if not sq.curr_song:
                await message.channel.send("No songs playing currently.")
                return
            skipped_song = sq.curr_song
            vc.stop()
        else:
            skip_idx = int(skip_idx) - 1
            if skip_idx < 0 or skip_idx >= len(sq.queue):
                await message.channel.send(f"Skip# has to be between {1} and {len(sq.queue)}.")
                return
            skipped_song = sq.queue[skip_idx]
            del sq.queue[skip_idx]

        await message.channel.send(f"Skipped '{skipped_song.title}'.")
    except Exception as e:
        await message.channel.send('Error Skipping: ' + str(e))

async def clear(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global sq
        if not sq.queue:
            await message.channel.send("Queue is already empty.")
            return

        sq.queue = deque([])
        await message.channel.send("Queue Cleared.")
    except Exception as e:
        await message.channel.send('Error Clearing Queue: ' + str(e))

async def disconnect(message, is_bot = False):
    try:
        if not is_bot and not await is_valid_command(message):
            return False

        channel = message
        if not is_bot:
            channel = channel.channel

        global vc
        if not vc:
            await channel.send("Already disconnected.")
            return
        
        await vc.disconnect() 

        global sq, loop_status, invalid_start
        vc = None
        sq = SongQueue()
        loop_status = LOOPDISABLED
        invalid_start = datetime.now()

        await asyncio.sleep(1)
        await channel.send("Bot Disconnected.")
    except Exception as e:
        await channel.send('Error Disconnecting: ' + str(e))

async def resume(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        if vc.is_paused():
            vc.resume()
            await message.channel.send('Bot Resumed.')
        else:
            await message.channel.send('Bot is not paused.')
    except Exception as e:
        await message.channel.send('Error Resuming: ' + str(e))

async def pause(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        if not vc.is_paused():
            vc.pause()
            await message.channel.send('Bot Paused.')
        else:
            await message.channel.send('Bot is already paused.')
    except Exception as e:
        await message.channel.send('Error Pausing: ' + str(e))

async def loop(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global loop_status
        if loop_status == LOOPDISABLED:
            loop_status = LOOPQUEUE
            await message.channel.send('Looped Queue.')
        elif loop_status == LOOPQUEUE:
            loop_status = LOOPSONG
            await message.channel.send('Looped Song.')
        elif loop_status == LOOPSONG:
            loop_status = LOOPDISABLED
            await message.channel.send('Disabled Loop.')
        else:
            raise Exception("Invalid loop state")
    except Exception as e:
        await message.channel.send('Error Looping: ' + str(e))

async def is_valid_command(message, check_bot_connected = False):
    try:
        if message.channel != ut.botChannel:
            await message.channel.send(f"Music Commands should only be in '{ut.botChannel.name}'", delete_after=300)
        elif not message.author.voice or not message.author.voice.channel:
            await message.channel.send('Please enter a voice channel')
        elif vc and ut.botObject.voice.channel != message.author.voice.channel:
            await message.channel.send('Please enter the same voice channel as the bot')
        elif not vc and check_bot_connected:
            await message.channel.send('Bot is not playing music currently')
        else:
            return True

        return False
    except Exception as e:
        await message.channel.send('Error Validating Music Command: ' + str(e))