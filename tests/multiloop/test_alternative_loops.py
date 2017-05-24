"""Unit tests for overriding the event loop."""
import asyncio

import pytest


@pytest.mark.asyncio
def test_for_custom_loop():
    """This test should be executed using the custom loop."""
    yield from asyncio.sleep(0.01)
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"


@pytest.mark.asyncio
@asyncio.coroutine
def test_dependent_fixture(dependent_fixture):
    yield from asyncio.sleep(0.1)
