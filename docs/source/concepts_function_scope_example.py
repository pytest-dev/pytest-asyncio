import asyncio

import pytest


@pytest.mark.asyncio
async def test_runs_in_a_loop():
    assert asyncio.get_running_loop()
