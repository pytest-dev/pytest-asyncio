import asyncio

import pytest

loop: asyncio.AbstractEventLoop


@pytest.mark.asyncio(scope="module")
async def test_remember_loop():
    global loop
    loop = asyncio.get_running_loop()


@pytest.mark.asyncio(scope="module")
async def test_runs_in_a_loop():
    global loop
    assert asyncio.get_running_loop() is loop
