from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
import discord

song_queue = []
songname = ""
text_channel = ""

# Consistenly Checking if the next song in queue should be played
async def play_song(voice):
    if (not voice.is_playing()) and (voice.is_connected()):
        global songname
        global text_channel
        if len(song_queue) > 0:
            song = song_queue.pop(0)
            YDL_OPTIONS = {'format': 'bestaudio','default_search':"ytsearch"}
            FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
            with YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(song, download=False)
            if 'entries' in info:
                url = info["entries"][0]["formats"][0]['url']
                songname = info["entries"][0]['title']
            elif 'formats' in info:
                url = info["formats"][0]['url']
                songname = info["entries"][0]['title']
            voice.play(FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
            await text_channel.send("Now Playing " + song)
        else:
            songname=""
                    
# Start playing a song or add it to queue
async def play(message):
    global song_queue
    global voice
    global songname
    global text_channel


    url = message.content[3:]
    YDL_OPTIONS = {'format': 'bestaudio','default_search':"ytsearch"}
    FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    user = message.author
    voice_channel = user.voice.channel
    text_channel = message.channel

    try:
        voice= await voice_channel.connect()
        song_queue =[]
    except Exception as e:
        pass

    if not voice.is_playing():
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)    
        if 'entries' in info:
            url = info["entries"][0]["formats"][0]['url']
            songname = info["entries"][0]['title']
        elif 'formats' in info:
            url = info["formats"][0]['url']
            songname = info["entries"][0]['title']
        voice.play(FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
        voice.is_playing()
        await message.channel.send(f"Bot is playing：{songname}")

    else:

        queue_len = len(song_queue)
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            songname2 = info["entries"][0]['title']
        elif 'formats' in info:
            songname2 = info["entries"][0]['title']
        if queue_len < 10000:
            song_queue.append(songname2)
            await message.channel.send(f"I am currently playing a song, this song has been added to the queue at position: {queue_len+1}.")
    
# display the current guilds queue 
async def queue(message):    
    if songname=="":
        await message.channel.send("There are currently no songs in the queue.")
    else:
        embed = discord.Embed(title="Song Queue", description="", colour=discord.Colour.dark_grey())
        embed.description += f"{1}) {songname}\n"

        i = 2
        
        for url in song_queue:
            embed.description += f"{i}) {url}\n"

            i += 1

        embed.set_footer(text="GeorgeChampBot"+ u"\u2122")
        await message.channel.send(embed=embed)

async def skip(message):
    if voice is None:
        return await message.channel.send("I am not playing any song.")
    else:
        voice.stop()

async def disconnect(message):
    if voice is None:
        return await message.channel.send("Bot is disconnected")
    else:
        await voice.disconnect()


async def join(message):
    global voice

    voice_channel = message.author.voice.channel
    try:
        voice= await voice_channel.connect()
    except Exception:
        await message.channel.send("Bot is connected")
    if voice and voice.is_connected():
        await voice.move_to(voice_channel)
    else:
        voice = await voice_channel.connect()


async def resume(message):
    global voice
    voice_channel = message.author.voice.channel
    try:
        voice= await voice_channel.connect()
    except Exception:
        await message.channel.send("Bot is connected")
    if not voice.is_playing():
        voice.resume()
        await message.channel.send('Bot is resuming')


async def pause(message):
    global voice
    voice_channel = message.author.voice.channel
    try:
        voice= await voice_channel.connect()
    except Exception:
        await message.channel.send("Bot is connected")
    if voice.is_playing():
        voice.pause()
        await message.channel.send('Bot has been paused')
