# GeorgeChampBot

GeorgeChampBot, a multi-purpose discord bot

## Getting Started

To get a copy of this project, install [git](https://git-scm.com/), and then run the following command in the terminal:

```
git clone https://github.com/george-xiao/GeorgeChampBot.git
```

Change your directory in the terminal to the cloned project:

```
cd your/path/here
```

Completely fill out all fields in the `.env` file. This will require you to set up the following:
 - a [Discord bot](https://discordpy.readthedocs.io/en/stable/discord.html), 
 - [Twitch Authentication Key](https://dev.twitch.tv/docs/authentication/),
 - [YouTube Authentication Key](https://developers.google.com/youtube/registering_an_application) and
 - Dedicated [server channels and roles](https://discord.com/blog/starting-your-first-discord-server)

Install [Docker](https://docs.docker.com/engine/install/) based on the platform the bot will run on.

Give the `run.sh` script permission to execute by running the following command in the terminal.

```
chmod +x run.sh
```

Finally, start the application using the `run.sh` script. Note that only this step is needed to start the bot on subsequent runs.

```
./run.sh
```

## Run Manually

To run the bot directly on your local machine, the additional dependencies have to be installed (on top the ones installed in [Getting Started](#getting-started)).

```
sudo apt-get install -y python3 python3-dev python3-pip
pip3 install -r requirements.txt
sudo apt-get install ffmpeg
```

Use the following command to start the bot:

```
python3 GeorgeChampBot.py
```

## Built With

* [asyncio](https://docs.python.org/3/library/asyncio.html) - write concurrent code using the async/await syntax 
* [collections](https://docs.python.org/3/library/collections.html) - specialized container datatypes providing alternatives to Python’s general purpose built-in containers
* [datetime](https://docs.python.org/3/library/datetime.html) - classes for manipulating dates and times
* [discord.py](https://discordpy.readthedocs.io/en/latest/) - API wrapper for Discord
* [dotenv](https://pypi.org/project/python-dotenv/) - reads the key-value pair from .env file
* [emoji](https://pypi.org/project/emoji/) - emojis for Python
* [google-api-python-client](https://pypi.org/project/google-api-python-client/) - Google API Python client library for Google's discovery based APIs
* [isodate](https://pypi.org/project/isodate/) - ISO 8601 date, time and duration parsing module
* [math](https://docs.python.org/3/library/math.html) - mathematical functions defined by the C standard
* [operator](https://docs.python.org/3/library/operator.html) - set of efficient functions corresponding to the intrinsic operators of Python
* [os](https://docs.python.org/3/library/os.html) - operating system dependent functionality
* [PyNaCl](https://pypi.org/project/PyNaCl/) - enables networking and cryptography operations
* [python-twitch-client](https://python-twitch-client.readthedocs.io/en/latest/) - Python library for accessing the Twitch API
* [re](https://docs.python.org/3/library/re.html) - regular expression matching operations
* [reqests](https://requests.readthedocs.io/en/master/) - HTTP requests
* [shelve](https://docs.python.org/3/library/shelve.html) - a persistent, dictionary-like object
* [urllib3](https://pypi.org/project/urllib3/) - a powerful, user-friendly HTTP client for Python
* [yt-dlp](https://pypi.org/project/yt-dlp/) - youtube-dl fork with additional features and fixes

## Authors

* **George Xiao** - [george-xiao](https://github.com/george-xiao)
* **Symoom Saad** - [PSYmoom](https://github.com/PSYmoom)
* **Maaz Mazharul** - [mmaaz1](https://github.com/mmaaz1)
* **Steven Aung** - [teiian](https://github.com/teiian)
