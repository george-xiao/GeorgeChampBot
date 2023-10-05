import shelve
import requests
import sys
sys.path.insert(1, '../common')
import common.utils as ut
from common.memberDatabase import MemberDatabase

twitch_OAuth_token = None
twitch_curr_livestreams = []
CONST_STREAMER_DB_PATH = './database/twitch_streamer_list.db'
streamerDatabase = MemberDatabase(CONST_STREAMER_DB_PATH)

async def check_twitch_live(channel):
    if not await validate_twitch_OAuth_token(channel):
        await generate_twitch_OAuth_token(channel)

    global twitch_OAuth_token
    global twitch_curr_livestreams

    try:
        streamer_list_shelf = shelve.open(CONST_STREAMER_DB_PATH)
        if streamer_list_shelf:
            twitch_streamers = '?user_login=' + '&user_login='.join(streamer_list_shelf.keys())
            headers = {
                'Client-ID': ut.env["TWITCH_CLIENT_ID"],
                'Authorization': 'Bearer ' + twitch_OAuth_token
            }

            stream = requests.get('https://api.twitch.tv/helix/streams' + twitch_streamers, headers=headers)
            stream = stream.json()

            fetched_livestreams = []        
            for livestream in stream.get('data'):
                fetched_livestreams.append(livestream['user_name'])
                if livestream['user_name'] not in twitch_curr_livestreams:
                    await channel.send(livestream['user_name'] + ' is live with ' + str(livestream['viewer_count']) + ' viewers! Go support them at https://twitch.tv/' + livestream['user_name'])

            twitch_curr_livestreams = fetched_livestreams
        streamer_list_shelf.close()
    except Exception as e:
        await channel.send('Error Obtaining Live Twitch Streamer List: ' + str(e))

async def validate_twitch_OAuth_token(channel):
    global twitch_OAuth_token

    if twitch_OAuth_token is not None:
        try:
            header = {
                'Authorization': 'OAuth ' + twitch_OAuth_token
            }

            response = requests.get('https://id.twitch.tv/oauth2/validate', headers=header)
            response = response.json()

            if 'status' in response and response.get('status') == 401:
                return False

            return True
        except Exception as e:
            await channel.send('Error Validating Twitch OAuth Token: ' + str(e))
    return False

async def generate_twitch_OAuth_token(channel):
    global twitch_OAuth_token

    twitch_OAuth_generation_body = {
        'client_id': ut.env["TWITCH_CLIENT_ID"],
        'client_secret': ut.env["TWITCH_CLIENT_SECRET"],
        "grant_type": 'client_credentials'
    }

    try:
        response = requests.post('https://id.twitch.tv/oauth2/token', twitch_OAuth_generation_body)
        response = response.json()
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
        result = streamerDatabase.add_item(message, admin_role, validate_userid_lamda)
        await ut.send_message(channel, result)
    except Exception as e:
        await ut.send_message(channel, "Error Adding Streamer: " + str(e))

# Helper Function for add_streamer
# Validates Twitch User Id
def validate_userid(streamer_userid, *valid_userid_args):
    twitch_streamers = '?login=' + streamer_userid
    user = requests.get('https://api.twitch.tv/helix/users' + twitch_streamers, headers=valid_userid_args[0])
    user = user.json()

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
    result = streamerDatabase.list_items()
    await ut.send_message(channel, result)
