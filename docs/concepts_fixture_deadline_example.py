import asyncio

import pytest

import pytest_asyncio


@pytest_asyncio.fixture
async def deadline():
    async with asyncio.timeout(1):
        yield


@pytest.mark.asyncio
async def test_finishes_before_the_deadline(deadline):
    await asyncio.sleep(0.01)
