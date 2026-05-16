import discord
import common.utils as ut
from components import emoteLeaderboard


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="transfer", description="Transfer score from a deleted emote to an existing one")
    @discord.app_commands.describe(
        emote_from="Source emote (must be deleted)", emote_to="Destination emote (must be active)"
    )
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def transfer(interaction: discord.Interaction, emote_from: str, emote_to: str):
        text = await emoteLeaderboard.transfer_emote_score(emote_from, emote_to)
        await interaction.response.send_message(text)

    transfer.autocomplete("emote_from")(emoteLeaderboard.deleted_emote_autocomplete)
    transfer.autocomplete("emote_to")(emoteLeaderboard.active_emote_autocomplete)
    transfer.error(ut.handle_command_error)
