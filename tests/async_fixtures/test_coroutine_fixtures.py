import asyncio
import unittest.mock

import pytest

START = object()
END = object()
RETVAL = object()

pytestmark = pytest.mark.skip(
    reason="@asyncio.coroutine fixtures are not supported yet"
)


@pytest.fixture
def mock():
    return unittest.mock.Mock(return_value=RETVAL)


@pytest.fixture
async def coroutine_fixture(mock):
    await asyncio.sleep(0.1, result=mock(START))


@pytest.mark.asyncio
async def test_coroutine_fixture(coroutine_fixture, mock):
    assert mock.call_count == 1
    assert mock.call_args_list[-1] == unittest.mock.call(START)
    assert coroutine_fixture is RETVAL
