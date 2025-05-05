"""
We support module-scoped async fixtures, but only if the event loop is
module-scoped too.
"""

from __future__ import annotations

import asyncio

import pytest

import pytest_asyncio


@pytest.fixture(scope="module")
def event_loop():
    """A module-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def async_fixture():
    await asyncio.sleep(0.1)
    return 1


@pytest.mark.asyncio
async def test_async_fixture_scope(async_fixture):
    assert async_fixture == 1
    await asyncio.sleep(0.1)
