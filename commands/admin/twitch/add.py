import discord
import common.utils as ut
from components import twitchAnnouncement


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="add", description="Add a Twitch streamer to the tracking list")
    @discord.app_commands.describe(user="Discord member who streams", twitch_username="Twitch username (login) to monitor")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def add(interaction: discord.Interaction, user: discord.Member, twitch_username: str):
        text = await twitchAnnouncement.add_streamer_to_db(user, twitch_username)
        await interaction.response.send_message(text)

    add.error(ut.handle_command_error)
