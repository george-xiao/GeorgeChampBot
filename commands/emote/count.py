import discord
from components import emoteLeaderboard
from common.utils import handle_slash_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="count", description="Show the all-time use count for an emote")
    @discord.app_commands.describe(emote="Pick from active server emotes")
    async def count(interaction: discord.Interaction, emote: str):
        text = await emoteLeaderboard.get_emote_count_text(emote)
        await interaction.response.send_message(text)

    count.autocomplete("emote")(emoteLeaderboard.active_emote_autocomplete)
    count.error(handle_slash_command_error)
