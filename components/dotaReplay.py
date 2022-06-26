import discord
import json
import math
import os
import requests
import shelve
from datetime import datetime
import sys
sys.path.insert(1, '../common')
import common.utils as ut

# This class (struct) stores the data for a given hero/player in a given game, and is used to construct the embed message
# in the DotaMatchMessage class
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

# This class takes a list of DotaHeroGameStats and a match id, and creates the embed message to be sent
class DotaMatchMessage:
    def __init__(self, dota_hero_game_stats, match_id: str):
        self.dota_hero_game_stats = dota_hero_game_stats
        self.match_id = match_id
        self.embedMsg = discord.Embed(title="")
        self.setEmbedMsg()


    def setEmbedMsg(self):
        if len(self.dota_hero_game_stats) == 0:
            return None

        hero_list = ut.create_json("../common/dota/hero_constants.json", __file__)
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
        self.embedMsg.description = self.dota_hero_game_stats[0].game_mode + " | " + side_win + " Win | " + ut.seconds_to_time(self.dota_hero_game_stats[0].duration)

        for index in range(len(self.dota_hero_game_stats)):
            hero_name = hero_list[self.dota_hero_game_stats[index].hero_id-1]['localized_name']
            field_desc = "K/D/A: " + str(self.dota_hero_game_stats[index].kills) + "/" + str(self.dota_hero_game_stats[index].deaths) + "/" + str(self.dota_hero_game_stats[index].assists) + " " + "XPM/GPM: " + str(self.dota_hero_game_stats[index].xpm) + "/" + str(self.dota_hero_game_stats[index].gpm)
            self.embedMsg.add_field(name=hero_name, value=field_desc, inline=True)

        self.embedMsg.set_thumbnail(url=hero_list[self.dota_hero_game_stats[0].hero_id-1]['img'])
        self.embedMsg.url = "https://dotabuff.com/matches/" + self.match_id


# Add a player to be tracked. The message should contain both the player's name and player id. Needs admin access
async def add_player(message, admin_role):
    try:
        channel = message.channel

        if not ut.author_is_admin(message.author, admin_role):
            await ut.send_message(channel, "Sorry, you need to be a dictator to use this command.")
            return

        invalid_message = "Invalid arguments. One should be a string of characters (no spaces), and one should be a number."
        # string parsing
        arg_list = ut.get_arg_list(message, 2, True)
        if not arg_list:
            await ut.send_message(channel, invalid_message)
            return

        first_arg = arg_list[0]
        second_arg = arg_list[1]

        if not(first_arg.isalpha() and second_arg.isdigit()):
            await ut.send_message(channel, invalid_message)
            return
                
        # shelf: {key = player id, value = player irl name}
        player_id = second_arg
        player_name = first_arg

        player_list_shelf = shelve.open('./database/dota_player_list.db')
        if player_list_shelf.get(player_id) is None:
            # add
            if player_id and player_name:
                player_list_shelf[player_id] = player_name
                await ut.send_message(channel, "Successfully added " + player_name)
            else:
                await ut.send_message(channel, invalid_message)
        else:
            await ut.send_message(channel, "This user already exists.")
        
        player_list_shelf.close()
    except Exception as e:
        await ut.mainChannel.send("Error Adding Player's Dotabuff: " + str(e))

# Remove a player from being tracked. The message should contain the player's name or player id. Needs admin access
async def remove_player(message, admin_role):
    try:
        channel = message.channel

        if not ut.author_is_admin(message.author, admin_role):
            await ut.send_message(channel, "Sorry, you need to be a dictator to use this command.")
            return

        invalid_message = "Invalid argument(s)"
        arg_list = ut.get_arg_list(message, 1, True)
        if not arg_list:
            await ut.send_message(channel, invalid_message)
            return

        first_arg = arg_list[0]

        # shelf: {key = player id, value = player irl name}
        player_id = first_arg if first_arg.isdigit() else ""
        player_name = "" if first_arg.isdigit() else first_arg

        player_list_shelf = shelve.open('./database/dota_player_list.db')
        if player_id:
            if player_list_shelf.get(player_id) is None:
                await ut.send_message(channel, "This user doesn't exist")
            else:
                del player_list_shelf[player_id]
                await ut.send_message(channel, "Successfully removed player " + str(player_id))
                successfully_removed = True
        elif player_name:
            successfully_removed = False
            for id, name in player_list_shelf.items():
                if name.lower() == player_name.lower():
                    del player_list_shelf[id]
                    await ut.send_message(channel, "Successfully removed player " + str(player_id))
                    successfully_removed = True
            if not successfully_removed:
                await ut.send_message(channel, "This user doesn't exist")
        else:
            await ut.send_message(channel, invalid_message)

        player_list_shelf.close()
    except Exception as e:
        await ut.mainChannel.send("Error Removing Player's Dotabuff: " + str(e))


# Lists the currently tracked players. Does not need admin access.
async def list_players(channel):
    player_list_shelf = shelve.open('./database/dota_player_list.db')
    msg = "Here's the current players we're tracking:\n"
    for player_id in player_list_shelf:
        msg += player_list_shelf[player_id] + ": " + player_id + "\n"

    player_list_shelf.close()
    msg = msg if msg else "The list of players is empty"
    await ut.send_message(channel, msg)

# The method that checks the recent matches for a timeframe and creates the messages accordingly
async def check_recent_matches(channel):
    try:
        open_dota_players_url = "https://api.opendota.com/api/players/"
        curr_epoch_time = int(datetime.now().timestamp())
        match_ids = {}
        match_hero_data_list = []
    
        game_mode_json = ut.create_json('../common/dota/game_mode_constants.json', __file__)

        player_list_shelf = shelve.open('./database/dota_player_list.db')
        for player in player_list_shelf.keys():
            res = requests.get(open_dota_players_url + player + '/recentMatches')
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 3610s (1h + 10s)
                    if curr_epoch_time - (int(match['start_time']) + int(match['duration'])) < 3610:
                        if str(match['match_id']) not in match_ids.keys():
                            match_hero_data = DotaHeroGameStats(match, game_mode_json[str(match['game_mode'])]['name'], player_list_shelf[player])
                            # match_ids.update({str(match['match_id']), [match_hero_data]})
                            match_ids[str(match['match_id'])] = [match_hero_data]
                        else:
                            match_ids[str(match['match_id'])].append(DotaHeroGameStats(match, game_mode_json[str(match['game_mode'])]['name'], player_list_shelf[player]))

        player_list_shelf.close()
        if match_ids.keys():
            hero_data_json = ut.create_json('../common/dota/hero_constants.json', __file__)
            await ut.send_message(channel, "Looks like DotA 2 is still alive! Here are the games from the last hour")
            for match_id in match_ids.keys():
                msg = DotaMatchMessage(match_ids[match_id], match_id)
                if msg is not None:
                    embedded_msg = msg.embedMsg
                    await ut.send_message(channel, "", embedded_msg)

    except Exception as e:
        await channel.send("Error Checking Recent Matches: " + str(e))
