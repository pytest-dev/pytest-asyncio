import asyncio

import pytest


@pytest.mark.asyncio_event_loop
class TestClassScopedLoop:
    loop: asyncio.AbstractEventLoop

    @pytest.mark.asyncio
    async def test_remember_loop(self):
        TestClassScopedLoop.loop = asyncio.get_running_loop()

    @pytest.mark.asyncio
    async def test_this_runs_in_same_loop(self):
        assert asyncio.get_running_loop() is TestClassScopedLoop.loop
