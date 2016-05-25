import asyncio
import pytest


@pytest.fixture(autouse=True)
def loop(loop):
    return loop


async def async_coro():
    await asyncio.sleep(0)
    return 'ok'


@pytest.mark.asyncio
async def test_autoused_loop():
    ret = await async_coro()
    assert ret == 'ok'
