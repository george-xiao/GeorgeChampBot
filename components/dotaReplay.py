import discord
import json
import math
import os
import requests
import shelve
from datetime import datetime
import sys

sys.path.insert(1, "../common")
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
        self.embedMsg.colour = 0x008000 if self.dota_hero_game_stats[0].this_player_won else 0xFF0000
        duration_mins = math.floor(self.dota_hero_game_stats[0].duration / 60)
        duration_secs = self.dota_hero_game_stats[0].duration % 60

        for index in range(len(self.dota_hero_game_stats)):
            title_arr.append(self.dota_hero_game_stats[index].player_name + " played " + hero_list[self.dota_hero_game_stats[index].hero_id - 1]["localized_name"])

        title_msg = " | ".join(title_arr)
        self.embedMsg.title = title_msg
        self.embedMsg.description = self.dota_hero_game_stats[0].game_mode + " | " + side_win + " Win | " + ut.seconds_to_time(self.dota_hero_game_stats[0].duration)

        for index in range(len(self.dota_hero_game_stats)):
            hero_name = hero_list[self.dota_hero_game_stats[index].hero_id - 1]["localized_name"]
            field_desc = "K/D/A: " + str(self.dota_hero_game_stats[index].kills) + "/" + str(self.dota_hero_game_stats[index].deaths) + "/" + str(self.dota_hero_game_stats[index].assists) + " " + "XPM/GPM: " + str(self.dota_hero_game_stats[index].xpm) + "/" + str(self.dota_hero_game_stats[index].gpm)
            self.embedMsg.add_field(name=hero_name, value=field_desc, inline=True)

        self.embedMsg.set_thumbnail(url=hero_list[self.dota_hero_game_stats[0].hero_id - 1]["img"])
        self.embedMsg.url = "https://dotabuff.com/matches/" + self.match_id


# Add a player to the tracking list. Returns the message to display to the user.
async def add_player(member: discord.Member, player_id: int) -> str:
    try:
        player_id_str = str(player_id)
        with shelve.open("./database/dota_player_list.db") as player_list_shelf:
            if player_list_shelf.get(player_id_str) is None:
                player_list_shelf[player_id_str] = member.name
                return f"Successfully added {member.name}"
            return "This user already exists."
    except Exception as e:
        return f"Error Adding Player's Dotabuff: {e}"


async def remove_player(player_id: str) -> str:
    try:
        with shelve.open("./database/dota_player_list.db") as player_list_shelf:
            if player_id in player_list_shelf:
                removed_name = player_list_shelf[player_id]
                del player_list_shelf[player_id]
                return f"Successfully removed {removed_name}"
            return f"{player_id} isn't being tracked"
    except Exception as e:
        return f"Error Removing Player's Dotabuff: {e}"


# Returns the text listing currently tracked players.
async def get_players_text() -> str:
    try:
        with shelve.open("./database/dota_player_list.db") as player_list_shelf:
            if len(player_list_shelf) == 0:
                return "The list of players is empty"
            msg = "Here's the current players we're tracking:\n"
            for player_id, member_name in player_list_shelf.items():
                msg += f"{member_name}: {player_id}\n"
            return msg
    except Exception as e:
        return f"Error Listing Players: {e}"


# The method that checks the recent matches for a timeframe and creates the messages accordingly
async def check_recent_matches(channel):
    try:
        open_dota_players_url = "https://api.opendota.com/api/players/"
        curr_epoch_time = int(datetime.now().timestamp())
        match_ids = {}

        game_mode_json = ut.create_json("../common/dota/game_mode_constants.json", __file__)

        player_list_shelf = shelve.open("./database/dota_player_list.db")
        for player_id, member_name in player_list_shelf.items():
            res = requests.get(open_dota_players_url + player_id + "/recentMatches")
            if res.status_code == 200:
                recent_matches = res.json()
                for match in recent_matches:
                    # if game in last 3610s (1h + 10s)
                    if curr_epoch_time - (int(match["start_time"]) + int(match["duration"])) < 3610:
                        match_id_str = str(match["match_id"])
                        hero_stats = DotaHeroGameStats(match, game_mode_json[str(match["game_mode"])]["name"], member_name)
                        if match_id_str not in match_ids:
                            match_ids[match_id_str] = [hero_stats]
                        else:
                            match_ids[match_id_str].append(hero_stats)

        player_list_shelf.close()
        if match_ids:
            await ut.send_message(channel, "Looks like DotA 2 is still alive! Here are the games from the last hour")
            for match_id, hero_stats_list in match_ids.items():
                msg = DotaMatchMessage(hero_stats_list, match_id)
                if msg is not None:
                    await ut.send_message(channel, "", msg.embedMsg)

    except Exception as e:
        await channel.send("Error Checking Recent Matches: " + str(e))


async def tracked_dota_player_autocomplete(interaction, current: str):
    matches = []
    with shelve.open("./database/dota_player_list.db") as player_list_shelf:
        for player_id, member_name in player_list_shelf.items():
            label = f"{member_name} (player {player_id})"
            if current.lower() in label.lower():
                matches.append((label, player_id))
    matches.sort()
    return [discord.app_commands.Choice(name=label, value=player_id) for label, player_id in matches[:25]]
