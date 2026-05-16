import discord
import common.utils as ut
from components import twitchAnnouncement


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="remove", description="Remove a tracked Twitch streamer")
    @discord.app_commands.describe(streamer="Pick from currently tracked streamers")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def remove(interaction: discord.Interaction, streamer: str):
        text = await twitchAnnouncement.remove_streamer_from_db(streamer)
        await interaction.response.send_message(text)

    remove.autocomplete("streamer")(twitchAnnouncement.tracked_twitch_streamer_autocomplete)
    remove.error(ut.handle_member_not_admin_error)
