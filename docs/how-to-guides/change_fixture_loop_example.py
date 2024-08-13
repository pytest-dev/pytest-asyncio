import asyncio

import pytest

import pytest_asyncio


@pytest_asyncio.fixture(loop_scope="module")
async def current_loop():
    return asyncio.get_running_loop()


@pytest.mark.asyncio(loop_scope="module")
async def test_runs_in_module_loop(current_loop):
    assert current_loop is asyncio.get_running_loop()
