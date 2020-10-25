from random import randrange
import shelve


async def play_music(message):
    playlist = shelve.open("youtube_playlist_shelf.db")
    played_playlist = shelve.open("youtube_played_playlist_shelf.db")

    randNum = str(randrange(0, len(playlist), 1))

    while randNum in played_playlist:
        randNum = await randrange(0, len(playlist), 1)
    played_playlist[playlist[randNum]] = playlist[randNum]
    if len(dict(playlist)) == len(dict(played_playlist)):
        played_playlist.clear()
    await message.channel.send("!play " + playlist[randNum])

    playlist.close()
    played_playlist.close()


async def add_music(message):
    playlist = shelve.open("youtube_playlist_shelf.db")
    played_playlist = shelve.open("youtube_played_playlist_shelf.db")

    songUrl = message.content[8:]
    flag = False
    for index in playlist:
        if playlist.get(index) == songUrl:
            flag = True
    if flag is False:
        playlist[str(len(dict(playlist)))] = songUrl
        await message.channel.send("Song added to the playlist!")
    else:
        await message.channel.send("Not added. Song is already in the playlist.")

    playlist.close()
    played_playlist.close()
