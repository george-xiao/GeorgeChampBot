import os, importlib
from discord import app_commands
import common.utils as ut

meme_group = app_commands.Group(name="meme", description="Meme review slash commands")


def register_group(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(meme_group)

    tree.add_command(meme_group, guild=ut.guildObject)
