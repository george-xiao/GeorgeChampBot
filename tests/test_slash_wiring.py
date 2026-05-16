"""Smoke tests that every slash command file's `register_subcommand` callable
runs without errors. Catches breakage from things like renaming a component
function and forgetting to update the slash wrapper — failures that don't
show up in snapshot tests (which call pure functions directly).
"""

import importlib
from pathlib import Path

import discord
import pytest


_COMMANDS_ROOT = Path(__file__).parent.parent / "commands"


def _discover_slash_modules():
    """Yield dotted module names for every leaf slash command file
    (per the auto-discovery rules: not __init__.py, not _-prefixed)."""
    repo_root = _COMMANDS_ROOT.parent
    for py_file in _COMMANDS_ROOT.rglob("*.py"):
        if py_file.name == "__init__.py" or py_file.name.startswith("_"):
            continue
        rel = py_file.relative_to(repo_root).with_suffix("")
        yield ".".join(rel.parts)


SLASH_MODULES = list(_discover_slash_modules())


@pytest.mark.parametrize("module_name", SLASH_MODULES, ids=SLASH_MODULES)
def test_slash_command_registers(module_name):
    module = importlib.import_module(module_name)
    assert hasattr(module, "register_subcommand"), (
        f"{module_name} must export register_subcommand(group)"
    )
    # Fresh group per test so registrations don't conflict.
    dummy_group = discord.app_commands.Group(name="test", description="test")
    module.register_subcommand(dummy_group)
