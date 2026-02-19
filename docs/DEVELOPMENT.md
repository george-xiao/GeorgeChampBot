# DEVELOPMENT.md

## Standard Development Process

See [Setup](../README.md#setup) and [Run Application Using Docker](../README.md#run-application-using-docker-recommended) in README to set up your development environment. The tools used for development (primarily Docker and less so GitBash) allows the application to be OS-agnostic. That being said, the application is hosted in a Linux-based environment so please keep that in mind while making changes in the repo.

### General Guidelines
- Use Docker when developing
- When modifying the `run.sh` script from a Windows environment, please ensure that it runs in a Linux environment (by using GitBash or similar tool to execute it)
- Run scripts from the project root directory

### Adding Slash Commands
> NOTE: Prefix commands (!<command>) have been deprecated in favor of slash commands (/<command>). Please take a moment to familiarize yourself with [slash commands](https://discordpy.readthedocs.io/en/stable/interactions/api.html#application-commands) before adding/modifying them in the repo.

**Structure:**
This is a simplified view of how slash commands are structured so that they can be dynamically loaded by the bot during runtime. Admin commands are hidden from everyone but people with ADMIN_ROLE. Notice how each command is defined in its own file.
```
commands/
├── movie/                            # /movie <command>
│   ├── __init__.py                   # Defines <movie> group, loads commands 
│   ├── <command1>.py
│   ├── ...
│   └── <commandN>.py
└── admin/
    ├── __init__.py                   # Defines admin group with permissions, loads subgroups
    └── movie/                        # /admin movie <command>
        ├── __init__.py               # Defines <movie> subgroup, loads commands in this folder
        ├── <command1>.py
        ├── ...
        └── <commandN>.py
```

To add slash commands for new features, you will need to create:
- a folder under `commands/` with all non-admin commands
- (Optional) a folder under `commands/admin/` if you have any admin commands
A new `__init__.py` will be required whenever you create a new folder.
```
commands/
├── movie/                            # /movie <command>
│   ├── __init__.py                   # Defines <movie> group, loads commands in this folder
│   ├── <command1>.py
│   ├── ...
│   └── <commandN>.py
├── <new_feature>/                    # /<new_feature> <command>
│   ├── __init__.py                   # Should define <new_feature> group, load commands in this folder
│   ├── <command1>.py
│   ├── ...
│   └── <commandN>.py
└── admin/
    ├── __init__.py                   # Defines admin group with permissions, loads subgroups
    ├── movie/                        # /admin movie <command>
    │   ├── __init__.py               # Defines <movie> subgroup, loads commands in this folder
    │   ├── <command1>.py
    │   ├── ...
    │   └── <commandN>.py
    └── <new_feature>/                # /admin <new_feature> <command>
        ├── __init__.py               # Defines <new_feature> subgroup, loads commands in this folder
        ├── <command1>.py
        ├── ...
        └── <commandN>.py
```

**Reference files:**
- `command/movie/__init__.py` - Defining a new group + Loading non-admin commands
- `command/movie/pick_movie.py` - Sample non-admin command with autocomplete
- `commands/admin/movie/__init__.py` - Defining a new subgroup + Loading admin commands
- `commands/admin/movie/pick_host.py` - Sample admin command with error handling

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