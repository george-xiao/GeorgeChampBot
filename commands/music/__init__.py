import os, importlib
from discord import app_commands
import common.utils as ut

music_group = app_commands.Group(name="music", description="Music player slash commands")


def register_group(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py" and not filename.startswith("_"):
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(music_group)

    tree.add_command(music_group, guild=ut.guildObject)
