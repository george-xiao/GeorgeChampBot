from discord import FFmpegPCMAudio
import googleapiclient.discovery
from yt_dlp import YoutubeDL
from collections import deque
from datetime import datetime
import sys

sys.path.insert(1, "../common")
import common.utils as ut
from urllib.parse import parse_qs, urlparse
import isodate
import discord
import random
from math import ceil

# Reference: https://github.com/yt-dlp/yt-dlp/blob/aa220d0aaac0f1562af658e34a28de72ec0ecb9f/yt_dlp/YoutubeDL.py#L199
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "default_search": "auto",
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": False,
    "source_address": "0.0.0.0",
    "noplaylist": True,
    "geo_bypass": True,
}

FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
MAX_SONGS = 1500
LOOPDISABLED = "LOOPDISABLED"
LOOPQUEUE = "LOOPQUEUE"
LOOPSONG = "LOOPSONG"
LOOPSTATES = [LOOPDISABLED, LOOPQUEUE, LOOPSONG]


class SongItem:
    """
    Represents a Song inside the queue.
    """

    def __init__(self, entry, requester):
        self.yt_url = f'https://www.youtube.com/watch?v={entry["id"]}'
        self.song_url = None
        self.title = entry["snippet"]["title"]
        self.channel_title = entry["snippet"]["channelTitle"]
        self.requester = requester
        self.duration = int(isodate.parse_duration(entry["contentDetails"]["duration"]).total_seconds())
        self.start_time = None  # in seconds

    def __str__(self):
        output = f"Name: {self.title}"
        output += f"Url: {self.yt_url}"
        output += f"Channel: {self.channel_title}"
        output += f"Requester: {self.requester}"
        output += f"Duration: {self.duration}"
        output += f"Start Time: {self.start_time}"
        return output


class SongQueue:
    """
    Represents a queue of SongItems.
    """

    def __init__(self):
        self.curr_song = None
        self.queue = deque([])


vc = None
sq = None
loop_status = None
should_disconnect = None


def reset_state():
    """
    Resets the state of the music player when the bot disconnects
    """
    global sq, vc, loop_status, should_disconnect
    sq = SongQueue()
    vc = None
    loop_status = 0
    should_disconnect = False


async def check_disconnect():
    """
    Disconnects the bot if it is alone or there are no songs in the queue
    """
    try:
        if not vc:
            return

        global should_disconnect
        if not sq.curr_song or (len(vc.channel.members) == 1):
            if should_disconnect:
                await _disconnect_internal()
                await ut.botChannel.send("Bot Disconnected.")
            else:
                should_disconnect = True
        else:
            should_disconnect = False
    except Exception as e:
        await ut.botChannel.send("Error Checking Disconnect: " + str(e))


async def play_song():
    """
    Plays song if previous one ends and queue is not empty
    """
    try:
        global sq
        while not await process_song(sq):
            pass
        if not vc or vc.is_playing() or vc.is_paused() or (not sq.queue and not sq.curr_song):
            return
        if not sq.queue and sq.curr_song:
            sq.curr_song = None
            return

        if LOOPSTATES[loop_status] == LOOPQUEUE:
            sq.queue.append(sq.curr_song)
        if LOOPSTATES[loop_status] == LOOPSONG:
            sq.queue.appendleft(sq.curr_song)
        sq.curr_song = sq.queue.popleft()

        sq.curr_song.start_time = datetime.now()
        vc.play(FFmpegPCMAudio(sq.curr_song.song_url, **FFMPEG_OPTIONS))
        embed = build_now_playing_embed()
        if embed is not None:
            await ut.botChannel.send(embed=embed, delete_after=sq.curr_song.duration)

    except Exception as e:
        await ut.botChannel.send("Error Playing Next Song: " + str(e))


# Constantly processing urls into sq
async def process_song(sq):
    """
    Downloads the song that is next up.

    Args:
        sq (SongQueue): Current queue

    Returns:
        bool: Whether the song was successfully downloaded
    """
    if not sq.queue:
        return True

    next_song = sq.queue[0]
    info = YoutubeDL(YDL_OPTIONS).extract_info(next_song.yt_url, download=False)
    if not info:
        await ut.botChannel.send(f"Skipped {next_song.title} ({next_song.yt_url}). Song is unavailable")
        sq.queue.popleft()
        return False

    for format in info["formats"]:
        if format["ext"] != "mhtml":
            break

    if format["ext"] == "mhtml":
        await ut.botChannel.send(f"Skipped {next_song.title} ({next_song.yt_url}). Video url couldn't be found")
        sq.queue.popleft()
        return False

    next_song.song_url = format["url"]
    return True


# Returns list of SongItems given input
async def process_input(user_input, requester):
    """
    Converts user's song requests into SongItems

    Args:
        user_input (str): Either a link or the name of the song
        requester (str): The name of the person who requested the song/playlist

    Returns:
        SongItem: The SongItem(s) that the user requested
    """

    video_ids = []
    query = parse_qs(urlparse(user_input).query, keep_blank_values=True)
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=ut.env["YOUTUBE_API_KEY"])
    if not query:
        request = youtube.search().list(part="id", maxResults=1, q=user_input)
        response = request.execute()
        if response["items"] and "videoId" in response["items"][0]["id"]:
            video_ids.append(response["items"][0]["id"]["videoId"])
    elif "youtube.com/watch" in user_input:
        video_ids.append(query["v"][0])
    if "youtube.com/playlist" in user_input:
        playlist_id = query["list"][0]
        request = youtube.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50)
        response = request.execute()
        while request is not None:
            response = request.execute()
            for item in response["items"]:
                video_ids.append(item["contentDetails"]["videoId"])
            request = youtube.playlistItems().list_next(request, response)
            if len(video_ids) > MAX_SONGS + 1:
                break

    if not video_ids:
        return []

    song_items = []
    for i in range(len(video_ids) // 50 + 1):
        start = i * 50
        end = min((i + 1) * 50, len(video_ids))
        request = youtube.videos().list(part="snippet,contentDetails", id=",".join(video_ids[start:end]), maxResults=50)

        while request is not None:
            response = request.execute()

            for item in response["items"]:
                song_items.append(SongItem(item, requester))
            request = youtube.playlistItems().list_next(request, response)
    return song_items


# === Pure functions called by slash commands. ===
# Each operates on the module-level globals (sq, vc, loop_status) and returns
# either a str, a list[str] for multi-message commands, or a discord.Embed.


async def play_song_request(user, voice_channel, query: str) -> list[str]:
    """
    Connects to voice if needed, then queues the requested song(s).
    Returns a list of user-visible messages (some commands send multiple).
    """
    global vc, sq
    try:
        print("Guild:", voice_channel.guild.id)
        print("Channel:", voice_channel.id)
        print("Bot voice state:", voice_channel.guild.me.voice)

        perms = voice_channel.permissions_for(voice_channel.guild.me)
        print("Connect:", perms.connect, "Speak:", perms.speak)

        if vc is None:
            vc = await voice_channel.connect()

        processed_songs = await process_input(query, user)
        added_songs = processed_songs[: MAX_SONGS - len(sq.queue)]
        sq.queue += added_songs

        messages = []
        if len(processed_songs) != len(added_songs):
            messages.append(f"{MAX_SONGS} song limit reached!")
        if len(processed_songs) == 0:
            messages.append(f"Couldn't find '{query}'")
        elif len(added_songs) == 1:
            messages.append(f"Added '{added_songs[0].title}' at position {len(sq.queue)}")
        else:
            messages.append(f"Added {len(added_songs)} songs.")
        return messages
    except Exception as e:
        return [f"Error Playing Song: {e}"]


def queue_response():
    """Returns either a str (empty queue) or a discord.Embed (queue page)."""
    return queue_response_page(1)


def queue_response_page(page: int = 1):
    try:
        if not sq.queue:
            return "Queue is empty."

        page_num = page - 1
        if page_num < 0:
            return "Page number out of range..."

        embed = discord.Embed(title="Queue", description="", colour=discord.Colour.dark_grey())
        start = page_num * 10
        end = min(len(sq.queue), (page_num + 1) * 10)
        for i in range(start, end):
            embed.description += f"{i+1}) {sq.queue[i].title}\n"
        embed.set_footer(text=f"Page {page_num+1}/{ceil(len(sq.queue)/10)}")

        if embed.description == "":
            return "Page number out of range..."
        return embed
    except Exception as e:
        return f"Error Printing Queue: {e}"


def build_now_playing_embed():
    """Returns either a str ('No songs playing currently.') or a discord.Embed."""
    try:
        if not sq.curr_song:
            return "No songs playing currently."

        song = sq.curr_song
        duration_time = ut.seconds_to_time(song.duration)
        elapsed = (datetime.now() - song.start_time).total_seconds() if song.start_time else 0
        curr_time = ut.seconds_to_time(elapsed)

        embed = discord.Embed(title="Now Playing", description=song.title, colour=discord.Colour.dark_grey())
        embed.set_footer(text=curr_time + "/" + duration_time)
        return embed
    except Exception as e:
        return f"Error Printing Now Playing: {e}"


def shuffle_queue() -> str:
    global sq
    try:
        if not sq.queue:
            return "Queue is empty."
        random.shuffle(sq.queue)
        return "Playlist Shuffled!"
    except Exception as e:
        return f"Error Shuffling: {e}"


def move_song(move_from: int, move_to: int = 1) -> str:
    global sq
    try:
        if not sq.queue:
            return "Queue is empty."

        move_from_idx = move_from - 1
        move_to_idx = move_to - 1

        if move_from_idx < 0 or move_from_idx >= len(sq.queue) or move_to_idx < 0 or move_to_idx >= len(sq.queue):
            return f"Index has to be between {1} and {len(sq.queue)}."

        moved_song = sq.queue[move_from_idx]
        del sq.queue[move_from_idx]
        sq.queue.insert(move_to_idx, moved_song)
        return f"Moved '{moved_song.title}' to position {move_to_idx + 1}!"
    except Exception as e:
        return f"Error Moving Song: {e}"


def skip_song(skip_idx: int = 0) -> str:
    global sq
    try:
        if skip_idx == 0:
            if not sq.curr_song:
                return "No songs playing currently."
            skipped_song = sq.curr_song
            if vc is not None:
                vc.stop()
            return f"Skipped '{skipped_song.title}'."

        idx = skip_idx - 1
        if idx < 0 or idx >= len(sq.queue):
            return f"Skip# has to be between {1} and {len(sq.queue)}."

        skipped_song = sq.queue[idx]
        del sq.queue[idx]
        return f"Skipped '{skipped_song.title}'."
    except Exception as e:
        return f"Error Skipping: {e}"


def clear_queue() -> str:
    global sq
    try:
        if not sq.queue:
            return "Queue is already empty."
        sq.queue = deque([])
        return "Queue Cleared."
    except Exception as e:
        return f"Error Clearing Queue: {e}"


async def _disconnect_internal():
    """Releases the voice client. Returns nothing."""
    global vc
    if vc is not None:
        await vc.disconnect()


async def disconnect_voice() -> str:
    global vc
    try:
        if vc is None:
            return "Already disconnected."
        await vc.disconnect()
        return "Bot Disconnected."
    except Exception as e:
        return f"Error Disconnecting: {e}"


def toggle_pause() -> str:
    try:
        if vc is None:
            return "Bot is not playing music currently"
        if not vc.is_paused():
            vc.pause()
            return "Bot Paused."
        else:
            vc.resume()
            return "Bot Resumed."
    except Exception as e:
        return f"Error Pausing: {e}"


def cycle_loop() -> str:
    global loop_status
    try:
        if LOOPSTATES[loop_status] == LOOPDISABLED:
            message = "Looped Queue."
        elif LOOPSTATES[loop_status] == LOOPQUEUE:
            message = "Looped Song."
        elif LOOPSTATES[loop_status] == LOOPSONG:
            message = "Disabled Loop."
        else:
            raise Exception("Invalid loop state")

        loop_status = (loop_status + 1) % 3
        return message
    except Exception as e:
        return f"Error Looping: {e}"
