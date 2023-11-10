import asyncio

import pytest

# Marks all test coroutines in this module
pytestmark = pytest.mark.asyncio


async def test_runs_in_asyncio_event_loop():
    assert asyncio.get_running_loop()
