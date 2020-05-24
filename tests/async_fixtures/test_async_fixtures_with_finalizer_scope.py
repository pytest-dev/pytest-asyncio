import asyncio
import contextlib
import functools
import pytest


@pytest.mark.asyncio
async def test_module_scope(port):
    await asyncio.sleep(0.01)
    assert port

@pytest.fixture(scope="module")
def event_loop():
    """Change event_loop fixture to module level."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def port(request, event_loop):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            await finalizer(None, None, None)
        event_loop.run_until_complete(port_afinalizer())

    context_manager = port_map()
    port = await context_manager.__aenter__()
    request.addfinalizer(functools.partial(port_finalizer, context_manager.__aexit__))
    return True


@contextlib.asynccontextmanager
async def port_map():
    worker = asyncio.create_task(asyncio.sleep(0.2))
    yield
    await worker
