# DEVELOPMENT.md

Currently, there is no standard development process. Make sure things are working locally using either `./run.sh` or `python3 GeorgeChampBot.py`.

To enter the `george_champ_bot_instance` image, run:

```
docker exec -it george_champ_bot_instance /bin/bash
```

## Update Dependencies

This project uses [pip-tools](https://pip-tools.readthedocs.io/) to manage dependencies. To update dependencies:

```
pip install pip-tools
pip-compile --upgrade requirements.in
```

## Built With

* [discord.py](https://discordpy.readthedocs.io/en/latest/) - Discord API wrapper
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube audio extraction for music player
* [google-api-python-client](https://github.com/googleapis/google-api-python-client) - YouTube API for video metadata
* [ffmpeg](https://ffmpeg.org/) - Audio processing for voice channels