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


@pytest.fixture(scope='module')
async def async_fixture_module_cope():
    return await asyncio.sleep(0.1, result=RETVAL)


@pytest.mark.asyncio
async def test_async_fixture_module_cope1(async_fixture_module_cope):
    assert async_fixture_module_cope is RETVAL


@pytest.mark.asyncio
@pytest.mark.xfail(reason='Only function scoped async fixtures are supported')
async def test_async_fixture_module_cope2(async_fixture_module_cope):
    assert async_fixture_module_cope is RETVAL