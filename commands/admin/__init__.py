import os, importlib
from discord import app_commands


def load_subcommands(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for subfolder in os.listdir(folder):
        path = os.path.join(folder, subfolder)
        if os.path.isdir(path):
            module_name = f"{__name__}.{subfolder}"
            module = importlib.import_module(module_name)
            if hasattr(module, "load_subcommands"):
                module.load_subcommands(tree)
