import asyncio

import pytest_asyncio


@pytest_asyncio.fixture
async def async_gen_fixture():
    await asyncio.sleep(0.1)
    yield "a value"


@pytest_asyncio.fixture(scope="module")
async def async_fixture():
    return await asyncio.sleep(0.1)
