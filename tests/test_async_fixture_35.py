import asyncio
import pytest
import pytest_asyncio


@pytest_asyncio.async_fixture
async def hello(loop):
    await asyncio.sleep(0, loop=loop)
    return 'hello'


def test_async_fixture(hello):
    assert hello == 'hello'
