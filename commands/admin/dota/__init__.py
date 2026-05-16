import os
import importlib
from discord import app_commands

dota_group = app_commands.Group(name="dota", description="Admin Dota tracking commands", parent=None)


def register_subgroup(admin_group: app_commands.Group):
    dota_group.parent = admin_group

    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(dota_group)

    admin_group.add_command(dota_group)
