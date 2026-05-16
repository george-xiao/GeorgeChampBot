# DEVELOPMENT.md

## Standard Development Process

See [Setup](../README.md#setup) and [Run Application Using Docker](../README.md#run-application-using-docker-recommended) in the README to set up your development environment.
The development workflow (primarily using Docker, and to a lesser extent GitBash) keeps the application OS-agnostic. That being said, the production environment is Linux-based, so please keep that in mind when making changes.

### General Guidelines
- Use Docker during development
- When modifying the `run.sh` on Windows, verify that it runs correctly in a Linux environment (by using GitBash or a similar tool to execute it)

### Adding new features
> NOTE: Prefix commands (!<command>) have been deprecated in favor of slash commands (/<command>). Before adding commands for your new feature, review the [slash command documentation](https://discordpy.readthedocs.io/en/stable/interactions/api.html#application-commands) and the [commands README](../commands/README.md).

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