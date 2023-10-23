import asyncio

import pytest

import pytest_asyncio


@pytest.mark.asyncio_event_loop
class TestClassScopedLoop:
    loop: asyncio.AbstractEventLoop

    @pytest_asyncio.fixture
    async def my_fixture(self):
        TestClassScopedLoop.loop = asyncio.get_running_loop()

    @pytest.mark.asyncio
    async def test_runs_is_same_loop_as_fixture(self, my_fixture):
        assert asyncio.get_running_loop() is TestClassScopedLoop.loop
