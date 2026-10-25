from __future__ import annotations

import pytest

pytest_plugins = "pytester"


@pytest.fixture
def pytester(
    pytester: pytest.Pytester,
    pytestconfig: pytest.Config,
    monkeypatch: pytest.MonkeyPatch,
) -> pytest.Pytester:
    """Run pytester sessions with the runner that this session uses."""
    if pytestconfig.getini("asyncio_experimental_task_per_fixture"):
        monkeypatch.setenv(
            "PYTEST_ADDOPTS", "-o asyncio_experimental_task_per_fixture=true"
        )
    return pytester
