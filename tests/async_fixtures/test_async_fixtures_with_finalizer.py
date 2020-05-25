import asyncio
import contextlib
import functools
import pytest


@pytest.mark.asyncio
async def test_module_with_event_loop_finalizer(port1):
    await asyncio.sleep(0.01)
    assert port1

@pytest.mark.asyncio
async def test_module_with_get_event_loop_finalizer(port2):
    await asyncio.sleep(0.01)
    assert port2

@pytest.fixture(scope="module")
def event_loop():
    """Change event_loop fixture to module level."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def port1(request, event_loop):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            # await task inside get_event_loop()
            # RantimeError is raised if task is created on a different loop
            await finalizer
        event_loop.run_until_complete(port_afinalizer())

    worker = asyncio.create_task(asyncio.sleep(0.2))
    request.addfinalizer(functools.partial(port_finalizer, worker))
    return True


@pytest.fixture(scope="module")
async def port2(request, event_loop):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            # await task inside get_event_loop()
            # if loop is different a RuntimeError is raised
            await finalizer
        asyncio.get_event_loop().run_until_complete(port_afinalizer())

    worker = asyncio.create_task(asyncio.sleep(0.2))
    request.addfinalizer(functools.partial(port_finalizer, worker))
    return True
