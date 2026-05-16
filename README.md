# GeorgeChampBot

GeorgeChampBot, a multi-purpose discord bot

## Setup

- To get a copy of this project, install [git](https://git-scm.com/), and then run the following command in the terminal:

```
git clone git@github.com:george-xiao/GeorgeChampBot.git
```

- Change your directory in the terminal to the cloned project:

```
cd your/path/here
```

- Copy the `.env.template` file to create a `.env` file, and fill in the `.env`. 

- This will require you to set up the following:
  - [A Discord bot](https://discordpy.readthedocs.io/en/stable/discord.html) (This bot uses some [Gateway Intents](https://discord.com/developers/docs/events/gateway#gateway-intents), so you will need to enable them as well.)
  - [Twitch Authentication Key](https://dev.twitch.tv/docs/authentication/),
  - [YouTube Authentication Key](https://developers.google.com/youtube/registering_an_application)
  - [Dedicated server channels and roles](https://discord.com/blog/starting-your-first-discord-server)

## Run Application Using Docker (Recommended)

- Install [Docker](https://docs.docker.com/engine/install/) based on the platform the bot will run on.

- (Windows only) Install [GitBash](https://git-scm.com/downloads) to execute shell scripts.

- Start the application using the `run.sh` script. If a container exists, you'll be prompted to either restart or view logs of the running service.

```
./run.sh
```

- To stop following logs, press `Ctrl+C`.

- To stop GeorgeChampBot, use the following command:

```
docker stop george_champ_bot_instance
```

## Run Application Locally (Not Recommended)
> NOTE: Please consider using Docker instead. Developers are testing their code on different OS. Docker allows us to be OS-agnostic.


- Install the system dependencies:

```
sudo apt-get install -y python3 python3-dev python3-pip ffmpeg python3-gdbm
```

- Then install the Python dependencies (you probably want to run this in a venv):

```
pip3 install -r requirements.txt
```

- Use the following command to start the bot:

```
python3 GeorgeChampBot.py
```

## Troubleshooting

**1. Music Player is no Longer Working** 

`yt-dlp` is known to break as Google changes things. It's a cat and mouse situation. You will need to [update dependencies](docs/DEVELOPMENT.md#updat-dependencies) so that the mouse can outmaneuver the cat. 

Use the following command to figure out the latest `yt-dlp` package version.

```
pip index versions yt-dlp
```

## Authors

* **George Xiao** - [george-xiao](https://github.com/george-xiao)
* **Symoom Saad** - [PSYmoom](https://github.com/PSYmoom)
* **Maaz Mazharul** - [mmaaz1](https://github.com/mmaaz1)
* **Simon Li** - [XiaoMengLiDev](https://github.com/XiaoMengLiDev)
* **Steven Aung** - [teiian](https://github.com/teiian) (<- **big cap**)
