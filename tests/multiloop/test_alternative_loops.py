"""Unit tests for overriding the event loop."""
import asyncio

import pytest


@pytest.mark.asyncio
def test_for_custom_loop(loop):
    """This test should be executed using the custom loop."""
    yield from asyncio.sleep(0.01, loop=loop)
    assert type(loop).__name__ == "CustomSelectorLoop"


@pytest.mark.asyncio
def test_forbid_global_loop(loop):
    """Test forbidding fetching the global loop using get_event_loop."""
    yield from asyncio.sleep(0.01, loop=loop)
    with pytest.raises(NotImplementedError):
        asyncio.get_event_loop()


@pytest.mark.asyncio(accept_global_loop=True)
def test_accept_global_loop(loop):
    """Test accepting fetching the global loop using get_event_loop."""
    yield from asyncio.sleep(0.01, loop=loop)
    global_loop = asyncio.get_event_loop()
    assert global_loop is loop


@pytest.mark.asyncio(accept_global_loop=True)
def test_no_loop_fixture():
    """Test accepting running the test coroutine when using the global loop
    is accepted and a loop fixture is not provided.
    """
    global_loop = asyncio.get_event_loop()
    yield from asyncio.sleep(0.01)
    assert True
