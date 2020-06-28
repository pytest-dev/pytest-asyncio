import asyncio
from asyncio.events import BaseDefaultEventLoopPolicy

import pytest


class CustomSelectorLoop(asyncio.SelectorEventLoop):
    """A subclass with no overrides, just to test for presence."""

    pass


class CustomSelectorLoopPolicy(BaseDefaultEventLoopPolicy):
    def new_event_loop(self):
        """Create a new event loop.

        You must call set_event_loop() to make this the current event
        loop.
        """
        return CustomSelectorLoop()


@pytest.fixture(autouse=True, scope="package")
def event_loop_policy():
    """Create an instance of the default event loop for each test case."""
    asyncio.set_event_loop_policy(CustomSelectorLoopPolicy())
    yield
    asyncio.set_event_loop_policy(None)
