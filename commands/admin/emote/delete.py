import discord
import common.utils as ut
from components import emoteLeaderboard


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="delete", description="Permanently delete a (already-soft-deleted) emote from the database")
    @discord.app_commands.describe(emote="Soft-deleted emote to permanently remove")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def delete(interaction: discord.Interaction, emote: str):
        text = await emoteLeaderboard.delete_emote_entry(emote)
        await interaction.response.send_message(text)

    delete.autocomplete("emote")(emoteLeaderboard.deleted_emote_autocomplete)
    delete.error(ut.handle_command_error)
