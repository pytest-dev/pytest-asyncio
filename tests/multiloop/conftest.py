import asyncio

import pytest


class CustomSelectorLoop(asyncio.SelectorEventLoop):
    """A subclass with no overrides, just to test for presence."""
    pass


@pytest.fixture()
def loop():
    """Create an instance of the default event loop for each test case."""
    return CustomSelectorLoop()
