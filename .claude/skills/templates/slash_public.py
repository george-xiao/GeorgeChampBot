"""Template for commands/<feature>/<name>.py (public slash command).

Copy to commands/<feature>/<name>.py and replace the placeholders:
  <module>           — components module providing the pure function
  <name>             — slash command name as users will see it
                        (e.g. leaderboard, count, list)
  <description>      — one-line user-visible description
  <pure_function>    — pure function in the component to call
  <arg>              — parameter(s) for the slash command
  <arg_description>  — help text shown in Discord's UI

The wrapper should be thin: call the pure function, send its result.
Snapshot tests target the pure function directly.
"""

import discord
from components import <module>
from common.utils import handle_slash_command_error


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="<name>", description="<description>")
    @discord.app_commands.describe(<arg>="<arg_description>")
    async def <name>(interaction: discord.Interaction, <arg>: str = ""):
        result = await <module>.<pure_function>(<arg>)
        await interaction.response.send_message(result)  # or embed=result

    <name>.error(handle_slash_command_error)
