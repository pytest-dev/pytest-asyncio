import asyncio

import pytest


def setup_module(module):
    asyncio.set_event_loop(None)


def teardown_module(module):
    # restore the default policy
    asyncio.set_event_loop_policy(None)


@pytest.fixture
def event_loop(request):
    loop = asyncio.new_event_loop()
    request.addfinalizer(loop.close)
    return loop


@asyncio.coroutine
def example_coroutine():
    return 42


@pytest.mark.asyncio
def test_asyncio_marker_with_non_global_loop(event_loop):
    with pytest.raises(RuntimeError):
        _ = asyncio.get_event_loop()

    result = yield from example_coroutine()

