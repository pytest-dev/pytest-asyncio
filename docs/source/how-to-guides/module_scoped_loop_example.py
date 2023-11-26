import asyncio

import pytest

pytestmark = pytest.mark.asyncio(scope="module")

loop: asyncio.AbstractEventLoop


async def test_remember_loop():
    global loop
    loop = asyncio.get_running_loop()


async def test_assert_same_loop():
    global loop
    assert asyncio.get_running_loop() is loop
