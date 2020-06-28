"""Unit tests for overriding the event loop."""
import asyncio

import pytest


@pytest.fixture
async def an_async_fixture():
    """An async fixture, to test if the loop is set correctly."""
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"
    yield 1


@pytest.mark.asyncio
async def test_for_custom_loop(an_async_fixture):
    """This test should be executed using the custom loop."""
    await asyncio.sleep(0.01)
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"


@pytest.mark.asyncio
async def test_dependent_fixture(dependent_fixture):
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_for_custom_loop_2():
    """This test should be executed using the custom loop."""
    await asyncio.sleep(0.01)
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"
