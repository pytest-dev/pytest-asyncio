import asyncio

import pytest


@pytest.mark.asyncio
async def test_runs_in_asyncio_event_loop():
    assert asyncio.get_running_loop()
