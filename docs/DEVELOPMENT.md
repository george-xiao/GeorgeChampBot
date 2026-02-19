# DEVELOPMENT.md

## Standard Development Process

### Prerequisites

- **Linux**: Docker installed
- **Windows**: Docker and GitBash (to execute shell scripts) installed

### Running the Bot

Start the bot using `./run.sh`. This script:
1. Checks if the container is already available and attaches to it if so
1. Creates the `database/` directory if it doesn't exist
1. Builds the Docker image `george_champ_bot`
1. Runs the container with the database directory mounted for persistence
1. Attaches to the container

To detach from the running container without stopping it, press `Ctrl+C`

### Stopping the Bot

Stop and remove the container using `./stop.sh`.

### Alternative (Local Development) (NOT RECOMMENDED)

Running the bot directly with `python3 GeorgeChampBot.py` is not recommended in development process. This is to ensure that the bot remains platform-agnostic. See the README for local setup instructions if this is unavoidable.

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