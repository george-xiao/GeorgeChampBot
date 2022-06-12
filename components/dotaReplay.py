import discord
import json
import math
import os
import requests
import shelve
from datetime import datetime
from . import utils as ut



def create_json(relative_file_path):
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, relative_file_path)
    file = open(filename)
    json_contents = json.load(file)
    file.close()
    return json_contents


class DotaHeroGameStats:
    def __init__(self, match_json, game_mode: str, player_name: str):
        self.kills = match_json["kills"]
        self.deaths = match_json["deaths"]
        self.assists = match_json["assists"]
        self.xpm = match_json["xp_per_min"]
        self.gpm = match_json["gold_per_min"]
        self.duration = match_json["duration"]
        self.game_mode = game_mode
        self.hero_id = match_json["hero_id"]
        self.radiant_win = match_json["radiant_win"]
        # OpenDota API specifications: https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1recentMatches%2Fget
        self.this_player_won = (match_json["radiant_win"] and match_json["player_slot"] < 128) or (not match_json["radiant_win"] and match_json["player_slot"] >= 128)
        self.player_name = player_name


class DotaMatchMessage:
    def __init__(self, dota_hero_game_stats, match_id: str):
        self.dota_hero_game_stats = dota_hero_game_stats
        self.match_id = match_id
        self.embedMsg = discord.Embed(title="")
        self.setEmbedMsg()


    def setEmbedMsg(self):
        if len(self.dota_hero_game_stats) == 0:
            return None

        hero_list = create_json("../common/dota/hero_constants.json")
        self.embedMsg.type = "rich"

        title_arr = []

        # this assumes we are all on the same team
        side_win = "Radiant" if self.dota_hero_game_stats[0].radiant_win else "Dire"
        self.embedMsg.colour = 0x008000 if self.dota_hero_game_stats[0].this_player_won else 0xff0000
        duration_mins = math.floor(self.dota_hero_game_stats[0].duration / 60)
        duration_secs = self.dota_hero_game_stats[0].duration % 60

        for index in range(len(self.dota_hero_game_stats)):
            title_arr.append(self.dota_hero_game_stats[index].player_name + " played " + hero_list[self.dota_hero_game_stats[index].hero_id-1]["localized_name"])

        title_msg = " | ".join(title_arr)
        self.embedMsg.title = title_msg
        self.embedMsg.description = self.dota_hero_game_stats[0].game_mode + " | " + side_win + " Win | " + str(duration_mins) + ":" + str(duration_secs)

        for index in range(len(self.dota_hero_game_stats)):
            hero_name = hero_list[self.dota_hero_game_stats[index].hero_id-1]['localized_name']
            field_desc = "K/D/A: " + str(self.dota_hero_game_stats[index].kills) + "/" + str(self.dota_hero_game_stats[index].deaths) + "/" + str(self.dota_hero_game_stats[index].assists) + " " + "XPM/GPM: " + str(self.dota_hero_game_stats[index].xpm) + "/" + str(self.dota_hero_game_stats[index].gpm)
            self.embedMsg.add_field(name=hero_name, value=field_desc, inline=True)

        self.embedMsg.set_thumbnail(url=hero_list[self.dota_hero_game_stats[0].hero_id-1]['img'])
        self.embedMsg.url = "https://dotabuff.com/matches/" + self.match_id


def get_arg_list(message, expected_num_args: int, strict: bool):
    arg_list = message.content.split()
    # ignore command
    if strict:
        arg_list = arg_list[1:expected_num_args+1]
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


async def send_message_embedded(channel, msg: str):
    try:
        await channel.send(embed=msg)
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
    if not arg_list:
        await send_message(channel, invalid_message)
        return

    first_arg = arg_list[0]
    second_arg = arg_list[1]

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
    match_ids = {}
    match_hero_data_list = []
    
    game_mode_json = create_json('../common/dota/game_mode_constants.json')

    try:
        player_list_shelf = shelve.open('./database/dota_player_list.db')
        for player in player_list_shelf.keys():
            res = requests.get(open_dota_players_url + player + '/recentMatches')
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 3610s (1h + 10s)
                    # if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 3610:
                    if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 86400:
                        if str(match['match_id']) not in match_ids.keys():
                            match_hero_data = DotaHeroGameStats(match, game_mode_json[str(match['game_mode'])]['name'], player_list_shelf[player])
                            # match_ids.update({str(match['match_id']), [match_hero_data]})
                            match_ids[str(match['match_id'])] = [match_hero_data]
                        else:
                            match_ids[str(match['match_id'])].append(DotaHeroGameStats(match, game_mode_json[str(match['game_mode'])]['name'], player_list_shelf[player]))

        player_list_shelf.close()
        if match_ids.keys():
            hero_data_json = create_json('../common/dota/hero_constants.json')
            for match_id in match_ids.keys():
                msg = DotaMatchMessage(match_ids[match_id], match_id)
                if msg is not None:
                    embedded_msg = msg.embedMsg
                    await send_message_embedded(channel, embedded_msg)

    except Exception as e:
        print(e)
        await channel.send("Looks like the opendota api is down or ur code is bugged. George pls fix.")
