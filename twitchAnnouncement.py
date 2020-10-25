import twitch


async def check_twitch_live(channel, TWITCH_CLIENT_ID, TWITCH_OAUTH_TOKEN, twitch_user_list):
    twitch_helix = twitch.TwitchHelix(client_id=TWITCH_CLIENT_ID, oauth_token=TWITCH_OAUTH_TOKEN)
    try:
        global twitch_curr_live
        res = twitch_helix.get_streams(user_logins=twitch_user_list)
        live_streams = []
        for stream_index in range(len(res)):
            live_streams.append(res[stream_index].user_name)
            if res[stream_index].user_name not in twitch_curr_live:
                await channel.send(res[stream_index].user_name + ' is live with ' + str(
                    res[stream_index].viewer_count) + ' viewers! Go support them at https://twitch.tv/' + res[
                                       stream_index].user_name)

        twitch_curr_live = live_streams
    except Exception as e:
        print(e)
