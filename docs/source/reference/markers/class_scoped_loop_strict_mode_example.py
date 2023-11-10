import asyncio

import pytest


@pytest.mark.asyncio(scope="class")
class TestClassScopedLoop:
    loop: asyncio.AbstractEventLoop

    async def test_remember_loop(self):
        TestClassScopedLoop.loop = asyncio.get_running_loop()

    async def test_this_runs_in_same_loop(self):
        assert asyncio.get_running_loop() is TestClassScopedLoop.loop
