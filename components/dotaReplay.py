import requests
import shelve
from datetime import datetime
from . import utils as ut


m_open_dota_api_key = ""

def get_arg_list(message, expected_num_args: int, strict: bool):
    arg_list = message.content.split()
    for item in arg_list:
        print(item)
    # ignore command
    if strict:
        arg_list = arg_list[1:expected_num_args+1]
        print(arg_list)
        if len(arg_list) != expected_num_args:
            return []
    else:
        arg_list = arg_list[1:]
        if len(arg_list) < expected_num_args:
            return []

    return arg_list


async def send_message(channel, msg: str):
    try:
        await channel.send(msg)
    except Exception as e:
        print(e)


def authorIsAdmin(author, admin_role: str):
    is_admin = False
    for role in author.roles:
        temp_admin_role = admin_role
        if role.name[0] != "@":
            temp_admin_role = admin_role[1:]
        if temp_admin_role == role.name:
            is_admin = True
    
    return is_admin


async def add_player(message, admin_role):
    channel = message.channel

    if not authorIsAdmin(message.author, admin_role):
        await send_message(channel, "Sorry, you need to be a dictator to use this command.")
        return

    invalid_message = "Invalid arguments. One should be a string of characters (no spaces), and one should be a number."
    # string parsing
    arg_list = get_arg_list(message, 2, True)
    print (arg_list)
    if not arg_list:
        await send_message(channel, invalid_message)
        return

    first_arg = arg_list[0]
    second_arg = arg_list[1]
    print(first_arg)
    print(second_arg)

    if not((first_arg.isdigit() and second_arg.isalpha()) or (first_arg.isalpha() and second_arg.isdigit())):
        await send_message(channel, invalid_message)
        return
            
    # shelf: {key = player id, value = player irl name}
    player_id = first_arg if first_arg.isdigit() else second_arg
    player_name = second_arg if first_arg.isdigit() else first_arg

    player_list_shelf = shelve.open('./database/dota_player_list.db')
    if player_list_shelf.get(player_id) is None:
        # add
        if player_id and player_name:
            player_list_shelf[player_id] = player_name
            await send_message(channel, "Successfully added " + player_name)
        else:
            await send_message(channel, invalid_message)
    else:
        await send_message(channel, "This user already exists.")
    
    player_list_shelf.close()


async def remove_player(message, admin_role):
    channel = message.channel

    if not authorIsAdmin(message.author, admin_role):
        await send_message(channel, "Sorry, you need to be a dictator to use this command.")
        return

    invalid_message = "Invalid argument(s)"
    arg_list = get_arg_list(message, 1, True)
    if not arg_list:
        await send_message(channel, invalid_message)
        return

    first_arg = arg_list[0]

    # shelf: {key = player id, value = player irl name}
    player_id = first_arg if first_arg.isdigit() else ""
    player_name = "" if first_arg.isdigit() else first_arg

    player_list_shelf = shelve.open('./database/dota_player_list.db')
    if player_id:
        if player_list_shelf.get(player_id) is None:
            await send_message(channel, "This user doesn't exist")
        else:
            del player_list_shelf[player_id]
            await send_message(channel, "Successfully removed player " + str(player_id))
            successfully_removed = True
    elif player_name:
        successfully_removed = False
        for id, name in player_list_shelf.items():
            if name.lower() == player_name.lower():
                del player_list_shelf[id]
                await send_message(channel, "Successfully removed player " + str(player_id))
                successfully_removed = True
        if not successfully_removed:
            await send_message(channel, "This user doesn't exist")
    else:
        await send_message(channel, invalid_message)

    player_list_shelf.close()


async def list_players(channel):
    player_list_shelf = shelve.open('./database/dota_player_list.db')
    msg = ""
    for player_id in player_list_shelf:
        msg += player_list_shelf[player_id] + ": " + player_id + "\n"

    player_list_shelf.close()
    msg = msg if msg else "The list of players is empty"
    await send_message(channel, msg)


async def check_recent_matches(channel):
    open_dota_players_url = "https://api.opendota.com/api/players/"
    curr_epoch_time = int(datetime.now().timestamp())
    match_ids = []
    
    try:
        player_list_shelf = shelve.open('./database/dota_player_list.db')
        for player in player_list_shelf:
            res = requests.get(open_dota_players_url + player + '/recentMatches')
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 3610s (1h + 10s)
                    if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 3610:
                        match_ids.append(str(match['match_id']))

        player_list_shelf.close()
        match_ids = list(set(match_ids))
        msg = "Looks like we have some DotA 2 players in this server... Here's the recent games played:\n"
        for match_id in match_ids:
            #delete match history after 1 day
            msg += "https://www.dotabuff.com/matches/" + match_id + "\n"
        
        await channel.send(msg, delete_after=86400)
    except Exception as e:
        await channel.send("Looks like the opendota api is down or ur code is bugged. George pls fix.")
