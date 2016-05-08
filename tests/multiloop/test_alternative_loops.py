"""Unit tests for overriding the event loop."""
import asyncio

import pytest


@pytest.mark.asyncio
def test_for_custom_loop():
    """This test should be executed using the custom loop."""
    yield from asyncio.sleep(0.01)
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"


@pytest.mark.asyncio(forbid_global_loop=True)
def test_forbid_global_loop(event_loop):
    """Test forbidding fetching the global loop using get_event_loop."""
    yield from asyncio.sleep(0.01, loop=event_loop)
    with pytest.raises(Exception):
        asyncio.get_event_loop()
