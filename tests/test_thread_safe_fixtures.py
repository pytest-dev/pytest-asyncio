import asyncio
import threading

import pytest


@pytest.fixture(scope="package")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    is_ready = threading.Event()

    def run_forever():
        is_ready.set()
        loop.run_forever()

    thread = threading.Thread(target=lambda: run_forever(), daemon=True)
    thread.start()
    is_ready.wait()
    yield loop


@pytest.fixture(scope="package")
async def async_fixture(event_loop):
    await asyncio.sleep(0)
    yield "fixture"


@pytest.mark.asyncio
async def test_event_loop_thread_safe(async_fixture):
    """Make sure that async fixtures still work, even if the event loop
    is running in another thread.
    """
    assert async_fixture == "fixture"
