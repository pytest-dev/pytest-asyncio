import asyncio

import pytest

import pytest_asyncio


@pytest.mark.asyncio(loop_scope="class")
class TestClassScopedLoop:
    loop: asyncio.AbstractEventLoop

    @pytest_asyncio.fixture(loop_scope="class")
    async def my_fixture(self):
        TestClassScopedLoop.loop = asyncio.get_running_loop()

    async def test_runs_is_same_loop_as_fixture(self, my_fixture):
        assert asyncio.get_running_loop() is TestClassScopedLoop.loop
