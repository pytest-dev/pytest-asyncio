# Code in this module does not perform any runtime assertions. It is solely intended
# to allow type checkers to report usage errors.
# This is necessary, because most other test code is hidden from type checkers
# through the use of pytest.Pytester
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator

import pytest_asyncio


@pytest_asyncio.fixture
async def coroutine() -> None:
    return None


@pytest_asyncio.fixture
async def async_generator0() -> AsyncGenerator:
    yield


@pytest_asyncio.fixture
async def async_generator1() -> AsyncIterator:
    yield


@pytest_asyncio.fixture
async def async_generator2() -> AsyncIterable:
    yield
