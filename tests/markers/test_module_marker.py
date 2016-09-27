"""Test if pytestmark works when defined in a module.

Pre-3.5 version.
"""
import asyncio

import pytest

pytestmark = pytest.mark.asyncio(forbid_global_loop=True)


class TestPyTestMark:
    @asyncio.coroutine
    def test_no_global_loop_method(self, event_loop, sample_fixture):
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop()
        counter = 1

        @asyncio.coroutine
        def inc():
            nonlocal counter
            counter += 1
            yield from asyncio.sleep(0, loop=event_loop)

        yield from asyncio.async(inc(), loop=event_loop)
        assert counter == 2

@asyncio.coroutine
def test_no_global_loop_coroutine(event_loop, sample_fixture):
    with pytest.raises(NotImplementedError):
        asyncio.get_event_loop()
    counter = 1

    @asyncio.coroutine
    def inc():
        nonlocal counter
        counter += 1
        yield from asyncio.sleep(0, loop=event_loop)

    yield from asyncio.async(inc(), loop=event_loop)
    assert counter == 2


@pytest.fixture
def sample_fixture():
    return None