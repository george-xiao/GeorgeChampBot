import pytest


@pytest.fixture(autouse=True)
def _noop_tasks(tasks_noop):
    """All command/event tests run with tasks disabled."""
    pass
