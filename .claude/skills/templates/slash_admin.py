"""Template for commands/admin/<feature>/<name>.py (admin-gated slash command).

Copy to commands/admin/<feature>/<name>.py and replace the placeholders:
  <module>           — components module providing the pure function
  <name>             — slash command name
  <description>      — one-line description
  <pure_function>    — pure function in the component to call
  <arg>              — parameter(s)
  <arg_description>  — help text

Admin role check is enforced by @has_role; non-admins are routed to
ut.handle_command_error via the .error handler.
"""

import discord
import common.utils as ut
from components import <module>


def register_subcommand(group: discord.app_commands.Group):
    @group.command(name="<name>", description="<description>")
    @discord.app_commands.describe(<arg>="<arg_description>")
    @discord.app_commands.checks.has_role(ut.env["ADMIN_ROLE"])
    async def <name>(interaction: discord.Interaction, <arg>: str):
        result = await <module>.<pure_function>(<arg>)
        await interaction.response.send_message(result)  # or embed=result

    <name>.error(ut.handle_command_error)
