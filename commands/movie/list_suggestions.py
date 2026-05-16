import discord
from components.movieNight import SUGGESTION_DATABASE, handle_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="list-suggestions", description="List everyone's suggestions")
    async def list_suggestions(interaction: discord.Interaction):
        reply = SUGGESTION_DATABASE.get_list_embed()
        await interaction.response.send_message(embed=reply)

    list_suggestions.error(handle_command_error)
