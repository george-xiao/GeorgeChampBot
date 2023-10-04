import shelve
import requests
import sys
sys.path.insert(1, '../common')
import common.utils as ut

twitch_OAuth_token = None
twitch_curr_livestreams = []
CONST_STREAMER_LIST = './database/twitch_streamer_list.db'

async def check_twitch_live(channel):
    if not await validateTwitchOAuthToken(channel):
        await generateTwitchOAuthToken(channel)
    
    global twitch_OAuth_token
    global twitch_curr_livestreams

    try:
        streamer_list_shelf = shelve.open(CONST_STREAMER_LIST)
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

async def validateTwitchOAuthToken(channel):
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

async def generateTwitchOAuthToken(channel):
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
        if not ut.author_is_admin(message.author, admin_role):
            await ut.send_message(channel, "Sorry, you need to be a dictator to use this command.")
            return

        invalid_message = "Invalid arguments. Name should be a string of characters (no spaces), and UserId should be a alphanumeric."
        # string parsing
        arg_list = ut.get_arg_list(message, 2, True)
        if not arg_list:
            await ut.send_message(channel, invalid_message)
            return

        first_arg = arg_list[0]
        second_arg = arg_list[1]

        if not(first_arg.isalpha() and second_arg.isalnum()):
            await ut.send_message(channel, invalid_message)
            return
                
        # shelf: {key = streamer's userid, value = streamer's irl name}
        streamer_userid = second_arg
        streamer_name = first_arg

        if not await valid_userid(channel, streamer_userid):
            await ut.send_message(channel, "Error! A streamer with userid " + streamer_userid + " does not exist.")
            return

        streamer_list_shelf = shelve.open(CONST_STREAMER_LIST)
        if streamer_list_shelf.get(streamer_userid) is None:
            # add
            if streamer_userid and streamer_name:
                streamer_list_shelf[streamer_userid] = streamer_name
                await ut.send_message(channel, "Successfully added " + streamer_name)
            else:
                await ut.send_message(channel, invalid_message)
        else:
            await ut.send_message(channel, "This streamer already exists.")
        
        streamer_list_shelf.close()
    except Exception as e:
        await ut.send_message(channel, "Error Adding Streamer: " + str(e))

# Validates Twitch User Id
async def valid_userid(channel, streamer_userid):
    if not await validateTwitchOAuthToken(channel):
        await generateTwitchOAuthToken(channel)
    
    global twitch_OAuth_token
    twitch_streamers = '?login=' + streamer_userid
    headers = {
        'Client-ID': ut.env["TWITCH_CLIENT_ID"],
        'Authorization': 'Bearer ' + twitch_OAuth_token
    }

    user = requests.get('https://api.twitch.tv/helix/users' + twitch_streamers, headers=headers)
    user = user.json()
    if user and len(user.get("data")) > 0:
        return True
    
    return False

# Remove a streaner from being tracked. The message should contain the streaner's name or userid. Needs admin access
async def remove_streamer(message, admin_role):
    channel = message.channel
    try:
        if not ut.author_is_admin(message.author, admin_role):
            await ut.send_message(channel, "Sorry, you need to be a dictator to use this command.")
            return

        invalid_message = "Invalid argument(s)"
        arg_list = ut.get_arg_list(message, 1, True)
        if not arg_list:
            await ut.send_message(channel, invalid_message)
            return

        first_arg = arg_list[0]
                
        # shelf: {key = streamer's userid, value = streamer's irl name}
        streamer_userid = "" if first_arg.isalpha() else first_arg
        streamer_name = first_arg if first_arg.isalpha() else ""

        streamer_list_shelf = shelve.open(CONST_STREAMER_LIST)
        if streamer_userid:
            if streamer_list_shelf.get(streamer_userid) is None:
                await ut.send_message(channel, "This user doesn't exist")
            else:
                streamer_name = streamer_list_shelf[streamer_userid]
                del streamer_list_shelf[streamer_userid]
                await ut.send_message(channel, "Successfully removed streamer: " + str(streamer_userid))
                successfully_removed = True
        elif streamer_name:
            successfully_removed = False
            for id, name in streamer_list_shelf.items():
                if name.lower() == streamer_name.lower():
                    del streamer_list_shelf[id]
                    await ut.send_message(channel, "Successfully removed streamer: " + str(id))
                    successfully_removed = True
            if not successfully_removed:
                await ut.send_message(channel, "This streamer doesn't exist")
        else:
            await ut.send_message(channel, invalid_message)

        streamer_list_shelf.close()
    except Exception as e:
        await ut.send_message(channel, "Error Removing Streamer: " + str(e))


# Lists the currently tracked streamers. Does not need admin access.
async def list_streamers(channel):
    streamer_list_shelf = shelve.open(CONST_STREAMER_LIST)
    
    if streamer_list_shelf:
        msg = "Here's the current streamers we're tracking:\n"
        for streamer_userid in streamer_list_shelf:
            msg += streamer_list_shelf[streamer_userid] + ": " + streamer_userid + "\n"
    else:
        msg = "The list of streamers is empty"
    
    streamer_list_shelf.close()
    await ut.send_message(channel, msg)