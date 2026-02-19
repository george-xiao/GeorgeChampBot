import os, importlib
from discord import app_commands

movie_group = app_commands.Group(name="movie", description="Admin movie night commands", parent=None)


def register_subgroup(admin_group: app_commands.Group):
    movie_group.parent = admin_group

    folder = os.path.dirname(__file__)
    for filename in os.listdir(folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"{__name__}.{filename[:-3]}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subcommand"):
                module.register_subcommand(movie_group)

    admin_group.add_command(movie_group)
