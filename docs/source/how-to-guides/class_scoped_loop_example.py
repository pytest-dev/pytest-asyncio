import asyncio

import pytest


@pytest.mark.asyncio(scope="class")
class TestInOneEventLoopPerClass:
    loop: asyncio.AbstractEventLoop

    async def test_remember_loop(self):
        TestInOneEventLoopPerClass.loop = asyncio.get_running_loop()

    async def test_assert_same_loop(self):
        assert asyncio.get_running_loop() is TestInOneEventLoopPerClass.loop
