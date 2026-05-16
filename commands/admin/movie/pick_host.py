import discord
import common.utils as ut
from components.movieNight import SUGGESTION_DATABASE
from components.subcomponents.movieNight import upcomingMovie


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="pick-host", description="Pick host for upcoming movie night")
    @discord.app_commands.describe(user="Host for upcoming movie night")
    @discord.app_commands.describe(prev_host="Bumps this user to the bottom of the list")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def pick_host(interaction: discord.Interaction, user: discord.Member, prev_host: discord.Member = None):
        if failed_embed := SUGGESTION_DATABASE.bump_prev_host(prev_host):
            await interaction.response.send_message(
                ut.get_role_str("ADMIN_ROLE"), embed=failed_embed, delete_after=ut.DEFAULT_MESSAGE_DURATION
            )
            return
        embed = await upcomingMovie.set_host(user.name)
        if prev_host:
            embed.description += (
                f"\n{ut.get_member_str(prev_host.name)} was successfully bumped to the end of the list!"
            )
        await interaction.response.send_message(embed=embed)

    pick_host.error(ut.handle_command_error)
