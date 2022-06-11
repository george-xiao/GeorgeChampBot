import twitch
from . import utils as ut

async def check_twitch_live(channel):
    twitchClientId = ut.env["TWITCH_CLIENT_ID"]
    twitchOAuthToken = ut.env["TWITCH_OAUTH_TOKEN"]
    twitchUserList = ut.env["twitch_user_list"]
    
    if not twitchClientId or not twitchOAuthToken:
        return
    twitch_helix = twitch.TwitchHelix(client_id=twitchClientId, oauth_token=twitchOAuthToken)
    try:
        global twitch_curr_live
        res = twitch_helix.get_streams(user_logins=twitchUserList)
        live_streams = []
        for stream_index in range(len(res)):
            live_streams.append(res[stream_index].user_name)
            if res[stream_index].user_name not in twitch_curr_live:
                await channel.send(res[stream_index].user_name + ' is live with ' + str(
                    res[stream_index].viewer_count) + ' viewers! Go support them at https://twitch.tv/' + res[
                                       stream_index].user_name)

        twitch_curr_live = live_streams
    except Exception as e:
        #TODO: Fix the error and print exception
        pass