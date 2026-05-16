import os, importlib
from discord import app_commands
import common.utils as ut

admin_group = app_commands.Group(name="admin", description="Admin commands", default_permissions=ut.get_role(ut.env["ADMIN_ROLE"]).permissions)


def register_group(tree: app_commands.CommandTree):
    folder = os.path.dirname(__file__)
    for subfolder in os.listdir(folder):
        path = os.path.join(folder, subfolder)
        if os.path.isdir(path):
            module_name = f"{__name__}.{subfolder}"
            module = importlib.import_module(module_name)
            if hasattr(module, "register_subgroup"):
                module.register_subgroup(admin_group)

    tree.add_command(admin_group, guild=ut.guildObject)