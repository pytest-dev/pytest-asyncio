import asyncio

import pytest

import pytest_asyncio


@pytest.mark.asyncio(scope="class")
class TestClassScopedLoop:
    loop: asyncio.AbstractEventLoop

    @pytest_asyncio.fixture(scope="class")
    async def my_fixture(self):
        TestClassScopedLoop.loop = asyncio.get_running_loop()

    async def test_runs_is_same_loop_as_fixture(self, my_fixture):
        assert asyncio.get_running_loop() is TestClassScopedLoop.loop
