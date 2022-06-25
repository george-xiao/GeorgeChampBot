import requests
import sys
sys.path.insert(1, '../common')
import common.utils as ut

twitch_OAuth_token = None
twitch_curr_livestreams = []

async def check_twitch_live(channel):
    if not await validateTwitchOAuthToken(channel):
        await generateTwitchOAuthToken(channel)
    
    global twitch_OAuth_token
    global twitch_curr_livestreams

    if twitch_OAuth_token:
        try:
            twitch_streamers = '?user_login=' + '&user_login='.join(ut.env["twitch_user_list"])
            headers = {
                'Client-ID': ut.env["TWITCH_CLIENT_ID"],
                'Authorization': 'Bearer ' + twitch_OAuth_token
            }

            stream = requests.get('https://api.twitch.tv/helix/streams' + twitch_streamers, headers=headers)
            stream = stream.json();

            fetched_livestreams = []        
            for livestream in stream['data']:
                fetched_livestreams.append(livestream['user_name'])
                if livestream['user_name'] not in twitch_curr_livestreams:
                    await channel.send(livestream['user_name'] + ' is live with ' + str(livestream['viewer_count']) + ' viewers! Go support them at https://twitch.tv/' + livestream['user_name'])

            twitch_curr_livestreams = fetched_livestreams
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

            if 'status' in response and response['status'] == 401:
                return False
            
            return True
        except Exception as e:
            await channel.send('Error Getting Twitch Streams: ' + str(e))
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