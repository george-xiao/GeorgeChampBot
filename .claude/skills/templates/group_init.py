"""Template for commands/<feature>/__init__.py (auto-discovery for a new feature group).

Copy to commands/<feature>/__init__.py and replace the placeholders:
  <feature>          — feature name (lowercase; appears as the slash group)
  <description>      — group description shown in Discord's UI

Drop subcommand files into the same directory; they'll be picked up
automatically as long as each defines a `register_subcommand(group)` function.
"""

import os, importlib
from discord import app_commands
import common.utils as ut

<feature>_group = app_commands.Group(name="<feature>", description="<description>")


def register_group(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(<feature>_group)

    tree.add_command(<feature>_group, guild=ut.guildObject)
