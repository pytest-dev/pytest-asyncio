import unittest.mock

import pytest

START = object()
END = object()
RETVAL = object()


@pytest.fixture(scope="module")
def mock():
    return unittest.mock.Mock(return_value=RETVAL)


@pytest.fixture
def var():
    contextvars = pytest.importorskip("contextvars")

    return contextvars.ContextVar("var_1")


@pytest.fixture
async def async_gen_fixture_within_context(mock, var):
    var.set(1)
    try:
        yield mock(START)
    except Exception as e:
        mock(e)
    else:
        mock(END)


@pytest.mark.asyncio
async def test_async_gen_fixture_within_context(
    async_gen_fixture_within_context, mock, var
):
    assert var.get() == 1
    assert mock.called
    assert mock.call_args_list[-1] == unittest.mock.call(START)
    assert async_gen_fixture_within_context is RETVAL


@pytest.mark.asyncio
async def test_async_gen_fixture_within_context_finalized(mock, var):
    with pytest.raises(LookupError):
        var.get()

    try:
        assert mock.called
        assert mock.call_args_list[-1] == unittest.mock.call(END)
    finally:
        mock.reset_mock()


@pytest.fixture
async def async_gen_fixture_1(var):
    var.set(1)
    yield


@pytest.fixture
async def async_gen_fixture_2(async_gen_fixture_1, var):
    assert var.get() == 1
    var.set(2)
    yield


@pytest.mark.asyncio
async def test_context_overwrited_by_another_async_gen_fixture(
    async_gen_fixture_2, var
):
    assert var.get() == 2


@pytest.fixture
async def async_fixture_within_context(async_gen_fixture_1, var):
    assert var.get() == 1


@pytest.fixture
def fixture_within_context(async_gen_fixture_1, var):
    assert var.get() == 1


@pytest.mark.asyncio
async def test_context_propagated_from_gen_fixture_to_normal_fixture(
    fixture_within_context, async_fixture_within_context
):
    pass


@pytest.fixture
def var_2():
    contextvars = pytest.importorskip("contextvars")

    return contextvars.ContextVar("var_2")


@pytest.fixture
async def async_gen_fixture_set_var_1(var):
    var.set(1)
    yield


@pytest.fixture
async def async_gen_fixture_set_var_2(var_2):
    var_2.set(2)
    yield


@pytest.mark.asyncio
async def test_context_modified_by_different_fixtures(
    async_gen_fixture_set_var_1, async_gen_fixture_set_var_2, var, var_2
):
    assert var.get() == 1
    assert var_2.get() == 2
