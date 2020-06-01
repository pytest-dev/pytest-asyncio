import asyncio
import functools
import pytest


@pytest.mark.asyncio
async def test_module_with_event_loop_finalizer(port_with_event_loop_finalizer):
    await asyncio.sleep(0.01)
    assert port_with_event_loop_finalizer

@pytest.mark.asyncio
async def test_module_with_get_event_loop_finalizer(port_with_get_event_loop_finalizer):
    await asyncio.sleep(0.01)
    assert port_with_get_event_loop_finalizer

@pytest.fixture(scope="module")
def event_loop():
    """Change event_loop fixture to module level."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def port_with_event_loop_finalizer(request, event_loop):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            # await task using loop provided by event_loop fixture
            # RuntimeError is raised if task is created on a different loop
            await finalizer
        event_loop.run_until_complete(port_afinalizer())

    worker = asyncio.ensure_future(asyncio.sleep(0.2))
    request.addfinalizer(functools.partial(port_finalizer, worker))
    return True


@pytest.fixture(scope="module")
async def port_with_get_event_loop_finalizer(request, event_loop):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            # await task using loop provided by asyncio.get_event_loop()
            # RuntimeError is raised if task is created on a different loop
            await finalizer
        asyncio.get_event_loop().run_until_complete(port_afinalizer())

    worker = asyncio.ensure_future(asyncio.sleep(0.2))
    request.addfinalizer(functools.partial(port_finalizer, worker))
    return True
