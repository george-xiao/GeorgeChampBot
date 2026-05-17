import discord
import common.utils as ut
from components import dotaReplay


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="remove", description="Remove a tracked Dota player")
    @discord.app_commands.describe(player="Pick from currently tracked players")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def remove(interaction: discord.Interaction, player: str):
        text = await dotaReplay.remove_player(player)
        await interaction.response.send_message(text)

    remove.autocomplete("player")(dotaReplay.tracked_dota_player_autocomplete)
    remove.error(ut.handle_command_error)
