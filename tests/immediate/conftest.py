"""Autouse fixtures for command/event-listeners tests.

Disable all background task scheduling so slash commands and gateway events can be tested without periodic/async tasks firing
"""

import pytest


@pytest.fixture(autouse=True)
def _noop_tasks(tasks_noop):
    """All command/event tests run with tasks disabled."""
    pass
