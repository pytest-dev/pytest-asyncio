import inspect

import pytest


def pytest_pycollect_makeitem(collector, name, obj):
    if inspect.iscoroutinefunction(obj) and name.startswith("test"):
        pytest.mark.asyncio(obj)
    return None
