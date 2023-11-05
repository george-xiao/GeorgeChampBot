import shelve
import sys
sys.path.insert(1, '../common')
import common.utils as ut
from common.memberDatabase import MemberDatabase

twitch_OAuth_token = None
# Key: User_Name; Value: discord.Message
twitch_curr_livestreams = {}
STREAMER_DB_PATH = './database/twitch_streamer_list.db'
streamerDatabase = MemberDatabase(STREAMER_DB_PATH)

async def check_twitch_live(channel):
    global twitch_OAuth_token
    global twitch_curr_livestreams

    try:
        # Need to generate OAuth token on startup and failed generation
        if not twitch_OAuth_token:
            await generate_twitch_OAuth_token(channel)

        streamer_list_shelf = shelve.open(STREAMER_DB_PATH)
        # Request list of live streamers currently online from Twitch
        # Documentation: https://dev.twitch.tv/docs/api/reference/#get-streams
        twitch_streamers = '?user_login=' + '&user_login='.join(streamer_list_shelf.keys())
        url = 'https://api.twitch.tv/helix/streams' + twitch_streamers
        headers = {
            'Client-ID': ut.env["TWITCH_CLIENT_ID"],
            'Authorization': 'Bearer ' + twitch_OAuth_token
        }

        stream = await ut.async_get_request(url, headers=headers)
        # Let stream fail once before generating twitch OAuth token
        # This will reduce the number of calls made by the application over time
        if not stream:
            if not await validate_twitch_OAuth_token(channel):
                await generate_twitch_OAuth_token(channel)
            stream = await ut.async_get_request(url, headers=headers)
        # If it fails with a newly generated OAuth, then Twitch is probably down
        if not stream:
            raise Exception("Twitch is probably not online. Ignoring request")

        # If livestream is new, create message
        # else update the viewer count
        fetched_livestreams = {}
        for livestream in stream.get('data'):
            user_name = livestream['user_name']
            if user_name not in twitch_curr_livestreams:
                message = await channel.send(generate_message(livestream))
            else:
                message = await twitch_curr_livestreams[user_name].edit(content=generate_message(livestream))
            fetched_livestreams[user_name] = message
        twitch_curr_livestreams = fetched_livestreams

        streamer_list_shelf.close()
    except Exception as e:
        await channel.send('Error Obtaining Live Twitch Streamer List: ' + str(e))

def generate_message(livestream):
    message_content = livestream["user_name"] + " is live"

    # Don't show viewer_count if it is zero :(
    if not livestream['viewer_count']:
        message_content += "!"
    else:
        message_content += " with " + str(livestream["viewer_count"]) + " viewers!"

    message_content += " Go support them at https://twitch.tv/" + livestream["user_name"]
    return message_content

async def validate_twitch_OAuth_token(channel):
    global twitch_OAuth_token

    if twitch_OAuth_token is not None:
        try:
            url = 'https://id.twitch.tv/oauth2/validate'
            headers = {
                'Authorization': 'OAuth ' + twitch_OAuth_token
            }

            response = await ut.async_get_request(url, headers=headers)

            if not response or ('status' in response and response.get('status')) == 401:
                return False

            return True
        except Exception as e:
            await channel.send('Error Validating Twitch OAuth Token: ' + str(e))
    return False

async def generate_twitch_OAuth_token(channel):
    global twitch_OAuth_token

    url = 'https://id.twitch.tv/oauth2/token'
    twitch_OAuth_generation_body = {
        'client_id': ut.env["TWITCH_CLIENT_ID"],
        'client_secret': ut.env["TWITCH_CLIENT_SECRET"],
        "grant_type": 'client_credentials'
    }

    try:
        response = await ut.async_post_request(url, twitch_OAuth_generation_body)
        twitch_OAuth_token = response['access_token']
    except Exception as e:
        await channel.send('Error Generating Twitch OAuth Token: ' + str(e))
        twitch_OAuth_token = None

# Add a streamer to be tracked. The message should contain both the streamer's userid and identifying name. Needs admin access
async def add_streamer(message, admin_role):
    channel = message.channel
    try:
        # userid validation work
        if not await validate_twitch_OAuth_token(channel):
            await generate_twitch_OAuth_token(channel)
        global twitch_OAuth_token
        headers = {
            'Client-ID': ut.env["TWITCH_CLIENT_ID"],
            'Authorization': 'Bearer ' + twitch_OAuth_token
        }
        validate_userid_lamda = lambda streamer_userid: validate_userid(streamer_userid, headers)

        # actual adding
        result = await streamerDatabase.add_item(message, admin_role, validate_userid_lamda)
        await ut.send_message(channel, result)
    except Exception as e:
        await ut.send_message(channel, "Error Adding Streamer: " + str(e))

# Helper Function for add_streamer
# Validates Twitch User Id
async def validate_userid(streamer_userid, *valid_userid_args):
    twitch_streamers = '?login=' + streamer_userid
    url = 'https://api.twitch.tv/helix/users' + twitch_streamers

    user = await ut.async_get_request(url, headers=valid_userid_args[0])

    if user and len(user.get("data")) > 0:
        return True

    return False

# Remove a streamer from being tracked. The message should contain the streamer's name or userid. Needs admin access
async def remove_streamer(message, admin_role):
    channel = message.channel
    try:
        result = streamerDatabase.remove_item(message, admin_role)
        await ut.send_message(channel, result)
    except Exception as e:
        await ut.send_message(channel, "Error Removing Streamer: " + str(e))


# Lists the currently tracked streamers. Does not need admin access.
async def list_streamers(channel):
    try:
        result = streamerDatabase.list_items()
        await ut.send_message(channel, result)
    except Exception as e:
        await ut.send_message(channel, "Error Retrieving Streamers: " + str(e))
