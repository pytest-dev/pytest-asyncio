import unittest.mock

import pytest
from async_generator import yield_, async_generator

START = object()
END = object()
RETVAL = object()


@pytest.fixture(scope='module')
def mock():
    return unittest.mock.Mock(return_value=RETVAL)


@pytest.fixture
@async_generator
async def async_gen_fixture(mock):
    try:
        await yield_(mock(START))
    except Exception as e:
        mock(e)
    else:
        mock(END)


@pytest.mark.asyncio
async def test_async_gen_fixture(async_gen_fixture, mock):
    assert mock.called
    assert mock.call_args_list[-1] == unittest.mock.call(START)
    assert async_gen_fixture is RETVAL


@pytest.mark.asyncio
async def test_async_gen_fixture_finalized(mock):
    try:
        assert mock.called
        assert mock.call_args_list[-1] == unittest.mock.call(END)
    finally:
        mock.reset_mock()
