import os
import importlib
from discord import app_commands


def load_commands(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for subfolder in os.listdir(folder):
        path = os.path.join(folder, subfolder)
        if os.path.isdir(path):
            module_name = f"{__name__}.{subfolder}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_group"):
                module.register_group(tree)
