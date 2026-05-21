"""Coverage guard: every registered slash command has an `invoke_slash`
test, and every command file is registered on the tree."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from discord import app_commands

import common.utils as ut


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / "commands"
TESTS_DIR = REPO_ROOT / "tests"

# Modal-only commands: their dispatch boundary is Modal.on_submit, not the
# tree. See docs/DEVELOPMENT.md "Common Patterns" → "Modal submission".
EXEMPT_COMMANDS = {"movie add-suggestion"}


def _walk_tree_paths(tree: app_commands.CommandTree) -> set[str]:
    paths: set[str] = set()

    def visit(cmd, prefix: list[str]) -> None:
        current = [*prefix, cmd.name]
        if isinstance(cmd, app_commands.Group):
            for child in cmd.commands:
                visit(child, current)
        else:
            paths.add(" ".join(current))

    for cmd in tree.get_commands(guild=ut.guildObject):
        visit(cmd, [])
    return paths


def _collect_invoked_paths() -> set[str]:
    paths: set[str] = set()
    for file in TESTS_DIR.glob("test_*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "invoke_slash"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                paths.add(node.args[1].value)
    return paths


def _command_files_with_register_subcommand():
    """Yield (path, leaf_name_or_None) per `commands/**/*.py` with a
    `register_subcommand` def. leaf_name comes from `@<group>.command(name=...)`."""
    for path in sorted(COMMANDS_DIR.rglob("*.py")):
        if path.name == "__init__.py" or path.name.startswith("_"):
            continue
        module = ast.parse(path.read_text(encoding="utf-8"))
        has_reg = any(
            isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == "register_subcommand"
            for n in module.body
        )
        if not has_reg:
            continue
        leaf = None
        for node in ast.walk(module):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            for dec in node.decorator_list:
                if not (
                    isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "command"
                ):
                    continue
                for kw in dec.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        leaf = kw.value.value
                        break
            if leaf is not None:
                break
        yield path, leaf


def test_every_registered_command_has_a_test(tree: app_commands.CommandTree) -> None:
    missing = sorted(_walk_tree_paths(tree) - _collect_invoked_paths() - EXEMPT_COMMANDS)
    if missing:
        bullets = "\n".join(f"  - /{p}" for p in missing)
        pytest.fail(
            f"Registered slash commands without an `invoke_slash` test:\n{bullets}\n\n"
            'Add `invoke_slash(tree, "<path>", user, guild, ...)` in tests/test_<feature>.py. '
            "See docs/DEVELOPMENT.md#adding-a-test.",
            pytrace=False,
        )


def test_every_command_file_is_registered(tree: app_commands.CommandTree) -> None:
    registered = _walk_tree_paths(tree)
    problems: list[str] = []
    for path, leaf in _command_files_with_register_subcommand():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if leaf is None:
            problems.append(f"  - {rel}: no `@group.command(name=...)` decorator found")
            continue
        feature = list(path.relative_to(COMMANDS_DIR).with_suffix("").parts[:-1])
        expected = " ".join([*feature, leaf])
        if expected not in registered:
            problems.append(f"  - {rel} → expected /{expected}, not on tree")
    if problems:
        bullets = "\n".join(problems)
        pytest.fail(
            f"Command files with `register_subcommand` not landing on the tree:\n{bullets}\n\n"
            "Check the parent `__init__.py` calls `register_subcommand(group)`, the file "
            "isn't filtered out by `_` prefix, and `@group.command(name=...)` matches.",
            pytrace=False,
        )
