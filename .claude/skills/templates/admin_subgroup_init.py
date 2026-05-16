"""Template for commands/admin/<feature>/__init__.py.

Copy to commands/admin/<feature>/__init__.py and replace the placeholders:
  <feature>          — feature name (lowercase)
  <description>      — subgroup description

Drop admin subcommand files into the same directory; they'll be picked up
automatically.
"""

import os, importlib
from discord import app_commands

<feature>_group = app_commands.Group(name="<feature>", description="<description>", parent=None)


def register_subgroup(admin_group: app_commands.Group):
    <feature>_group.parent = admin_group

    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(<feature>_group)

    admin_group.add_command(<feature>_group)
