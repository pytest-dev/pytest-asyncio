from __future__ import annotations

import asyncio
import unittest.mock

import pytest

START = object()
END = object()
RETVAL = object()


@pytest.fixture
def mock():
    return unittest.mock.Mock(return_value=RETVAL)


@pytest.fixture
async def async_fixture(mock):
    return await asyncio.sleep(0.1, result=mock(START))


@pytest.mark.asyncio
async def test_async_fixture(async_fixture, mock):
    assert mock.call_count == 1
    assert mock.call_args_list[-1] == unittest.mock.call(START)
    assert async_fixture is RETVAL


class TestAsyncFixtureMethod:
    is_same_instance = False

    @pytest.fixture(autouse=True)
    async def async_fixture_method(self):
        self.is_same_instance = True

    @pytest.mark.asyncio
    async def test_async_fixture_method(self):
        assert self.is_same_instance


@pytest.fixture()
async def setup_and_teardown_tasks():
    task = asyncio.current_task()
    yield
    assert task is asyncio.current_task()


async def test_setup_and_teardown_tasks(setup_and_teardown_tasks):
    pass
