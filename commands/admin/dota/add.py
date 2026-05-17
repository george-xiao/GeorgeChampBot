import discord
import common.utils as ut
from components import dotaReplay


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="add", description="Add a Dota player to the tracking list")
    @discord.app_commands.describe(user="Discord member to track", player_id="OpenDota account ID")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def add(interaction: discord.Interaction, user: discord.Member, player_id: int):
        text = await dotaReplay.add_player(user, player_id)
        await interaction.response.send_message(text)

    add.error(ut.handle_command_error)
