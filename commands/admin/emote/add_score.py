import discord
import common.utils as ut
from components import emoteLeaderboard


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="add-score", description="Manually add to an emote's all-time score")
    @discord.app_commands.describe(emote="Active emote to adjust", score="Score to add (can be negative)")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def add_score(interaction: discord.Interaction, emote: str, score: int):
        text = await emoteLeaderboard.add_emote_score(emote, score)
        await interaction.response.send_message(text)

    add_score.autocomplete("emote")(emoteLeaderboard.active_emote_autocomplete)
    add_score.error(ut.handle_member_not_admin_error)
