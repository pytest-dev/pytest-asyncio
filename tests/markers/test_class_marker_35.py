"""Test if pytestmark works when defined on a class."""
import asyncio
import pytest


class TestPyTestMark:
    pytestmark = pytest.mark.asyncio(forbid_global_loop=True)

    async def test_no_global_loop(self, event_loop, sample_fixture):
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop()
        counter = 1
        async def inc():
            nonlocal counter
            counter += 1
            await asyncio.sleep(0, loop=event_loop)
        await asyncio.ensure_future(inc(), loop=event_loop)
        assert counter == 2


@pytest.fixture
def sample_fixture():
    return None