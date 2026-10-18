"""Config guard: .env.template, the env vars common/utils.py reads, and the
test placeholders all list the same keys."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from tests._env_setup import _PLACEHOLDERS


REPO_ROOT = Path(__file__).resolve().parent.parent


def _template_keys() -> set[str]:
    text = (REPO_ROOT / ".env.template").read_text()
    return set(re.findall(r"^([A-Z_]+)=", text, flags=re.MULTILINE))


def _keys_read_by_utils() -> set[str]:
    tree = ast.parse((REPO_ROOT / "common" / "utils.py").read_text())
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "getenv"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }


def test_template_matches_keys_read_by_utils():
    template, code = _template_keys(), _keys_read_by_utils()
    assert code - template == set(), "read by common/utils.py but missing from .env.template"
    assert template - code == set(), "in .env.template but never read by common/utils.py"


def test_placeholders_match_template():
    assert set(_PLACEHOLDERS) == _template_keys()
