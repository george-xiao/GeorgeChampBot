import os, importlib
from discord import app_commands
import common.utils as ut

admin_movie_group = app_commands.Group(name="admin-movie", description="Admin movie night commands")


def load_subcommands(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(admin_movie_group)

    tree.add_command(admin_movie_group, guild=ut.guildObject)
