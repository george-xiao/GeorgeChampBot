import requests
import shelve
from datetime import datetime

async def check_recent_matches(channel, player_list, OPENDOTA_API_KEY):
    s = shelve.open('./database/george_token_count.db')
    if s.get("token_count") is None:
        s["token_count"] = 0

    open_dota_players_url = "https://api.opendota.com/api/players/"
    curr_epoch_time = int(datetime.now().timestamp())
    hed = {'Authorization': 'Bearer ' + OPENDOTA_API_KEY}
    match_ids = []
    
    try:
        for player in player_list:
            res = requests.get(open_dota_players_url + player + '/recentMatches', headers=hed)
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 3610s (1h + 10s)
                    if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 3610:
                        if (player == "257091712") :
                            s["token_count"] += 1
                        if (player == "176471411") : 
                            s["token_count"] -= 1
                        match_ids.append(str(match['match_id']))

        s.close()
        match_ids = list(set(match_ids))
        for match_id in match_ids:
            #delete match history after 1 day
            await channel.send(
                "Looks like someone played a game... Here's the match:\nhttps://www.dotabuff.com/matches/" + str(
                match_id), delete_after=86400)
    except Exception as e:
        await channel.send("Looks like the opendota api is down or ur code is bugged. George pls fix.")


async def print_tokens(channel):
    try:
        s = shelve.open('./database/george_token_count.db')
        if s.get("token_count") is None:
            s["token_count"] = 0
        
        num_tokens = s["token_count"]
        if (num_tokens == 1) :
            await channel.send("You have 1 token.")
        else : 
            await channel.send("You have " + str(num_tokens) + " tokens.")
        s.close()
    except Exception as e:
        await channel.send("george pls")
