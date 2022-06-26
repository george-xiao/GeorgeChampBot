from discord import FFmpegPCMAudio
import googleapiclient.discovery
from yt_dlp import YoutubeDL
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


YDL_OPTIONS = {'format': 'bestaudio/best', 'default_search': 'auto', 'quiet': 'True', 'no_warnings': 'True',
'ignoreerrors': 'False', 'source_address': '0.0.0.0', 'nocheckcertificate': 'True', "noplaylist": 'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
MAX_SONGS = 1500
LOOPDISABLED = "LOOPDISABLED"
LOOPQUEUE = "LOOPQUEUE"
LOOPSONG = "LOOPSONG"
LOOPSTATES = [LOOPDISABLED, LOOPQUEUE, LOOPSONG]


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

vc = None
sq = None
loop_status = None
should_disconnect = None

def reset_state():
    global sq, vc, loop_status, should_disconnect
    sq = SongQueue()
    vc = None
    loop_status = 0
    should_disconnect = False

async def check_disconnect():
    try:
        if not vc:
            return
        
        global should_disconnect
        if not sq.curr_song or (len(vc.channel.members) == 1):
            if should_disconnect:
                await disconnect(ut.botChannel, is_bot=True)
            else:
                should_disconnect = True
        else:
            should_disconnect = False
    except Exception as e:
        await ut.botChannel.send('Error Checking Disconnect: ' + str(e))
    

# Constantly checking if the next song in queue should be played
async def play_song():
    try:
        global sq
        while not await process_song(sq):
            pass
        if not vc or vc.is_playing() or vc.is_paused() or (not sq.queue and not sq.curr_song):
            return
        if not sq.queue and sq.curr_song:
            sq.curr_song = None
            return

        if (LOOPSTATES[loop_status] == LOOPQUEUE):
            sq.queue.append(sq.curr_song)
        if (LOOPSTATES[loop_status] == LOOPSONG):
            sq.queue.appendleft(sq.curr_song)
        sq.curr_song = sq.queue.popleft()

        sq.curr_song.start_time = datetime.now()
        vc.play(FFmpegPCMAudio(sq.curr_song.song_url, **FFMPEG_OPTIONS))
        await now_playing(ut.botChannel, delete_after=sq.curr_song.duration, is_bot=True)

    except Exception as e:
        await ut.botChannel.send('Error Playing Next Song: ' + str(e))

# Constantly processing urls into sq
async def process_song(sq):
    if not sq.queue:
        return True

    next_song = sq.queue[0]
    info = YoutubeDL(YDL_OPTIONS).extract_info(next_song.yt_url, download=False)
    if not info:
        await ut.botChannel.send(f'Skipped {next_song.title} ({next_song.yt_url}). Song is unavailable')
        sq.queue.popleft()
        return False
    
    for format in info["formats"]:
        if format["ext"] != "mhtml": break

    if format["ext"] == "mhtml":
        await ut.botChannel.send(f"Skipped {next_song.title} ({next_song.yt_url}). Video url couldn't be found")
        sq.queue.popleft()
        return False

    next_song.song_url = format["url"]
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
        if not vc:
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
    
async def move(message, message_content):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global sq
        if not sq.queue:
            await message.channel.send("Queue is empty.")
            return

        message_content = message_content.split()
        move_from = int(message_content[0]) - 1
        if len(message_content) > 1:
            move_to = int(message_content[1]) - 1
        else:
            move_to = 0

        if move_from < 0 or move_from >= len(sq.queue) or move_to < 0 or move_to >= len(sq.queue):
            await message.channel.send(f"Index has to be between {1} and {len(sq.queue)}.")
            return

        moved_song = sq.queue[move_from]
        del sq.queue[move_from]
        sq.queue.insert(move_to, moved_song)
        await message.channel.send(f"Moved '{moved_song.title}' to position {move_to+1}!")
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
            if not is_bot:
                await channel.send("Already disconnected.")
            return
        
        await vc.disconnect()
        await channel.send("Bot Disconnected.")
    except Exception as e:
        await channel.send('Error Disconnecting: ' + str(e))

async def pause(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        if not vc.is_paused():
            vc.pause()
            await message.channel.send('Bot Paused.')
        else:
            vc.resume()
            await message.channel.send('Bot Resumed.')
    except Exception as e:
        await message.channel.send('Error Pausing: ' + str(e))

async def loop(message):
    try:
        if not await is_valid_command(message, check_bot_connected = False):
            return False

        global loop_status
        if LOOPSTATES[loop_status] == LOOPDISABLED:
            await message.channel.send('Looped Queue.')
        elif LOOPSTATES[loop_status] == LOOPQUEUE:
            await message.channel.send('Looped Song.')
        elif LOOPSTATES[loop_status] == LOOPSONG:
            await message.channel.send('Disabled Loop.')
        else:
            raise Exception("Invalid loop state")
        
        loop_status = (loop_status + 1) % 3

    except Exception as e:
        await message.channel.send('Error Looping: ' + str(e))

async def is_valid_command(message, check_bot_connected = False):
    try:
        if message.channel != ut.botChannel:
            await message.channel.send(f"Music Commands should only be in '{ut.botChannel.name}'")
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