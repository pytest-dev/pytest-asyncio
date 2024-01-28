"""
We support module-scoped async fixtures, but only if the event loop is
module-scoped too.
"""

import asyncio

import pytest


@pytest.fixture(scope="module")
def event_loop():
    """A module-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def async_fixture():
    await asyncio.sleep(0.1)
    return 1


@pytest.mark.asyncio
async def test_async_fixture_scope(async_fixture):
    assert async_fixture == 1
    await asyncio.sleep(0.1)
