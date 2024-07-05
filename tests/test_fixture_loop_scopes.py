import asyncio

import pytest

import pytest_asyncio

loop: asyncio.AbstractEventLoop


@pytest_asyncio.fixture(loop_scope="session")
async def fixture():
    global loop
    loop = asyncio.get_running_loop()


@pytest.mark.asyncio(scope="session")
async def test_fixture_loop_scopes(fixture):
    global loop
    assert loop == asyncio.get_running_loop()
