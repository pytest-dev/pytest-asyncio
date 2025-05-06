from __future__ import annotations

import asyncio
import functools

import pytest

import pytest_asyncio


@pytest.mark.asyncio(loop_scope="module")
async def test_module_with_event_loop_finalizer(port_with_event_loop_finalizer):
    await asyncio.sleep(0.01)
    assert port_with_event_loop_finalizer


@pytest.mark.asyncio(loop_scope="module")
async def test_module_with_get_event_loop_finalizer(port_with_get_event_loop_finalizer):
    await asyncio.sleep(0.01)
    assert port_with_get_event_loop_finalizer


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def port_with_event_loop_finalizer(request):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            # await task using loop provided by event_loop fixture
            # RuntimeError is raised if task is created on a different loop
            await finalizer

        asyncio.run(port_afinalizer())

    worker = asyncio.ensure_future(asyncio.sleep(0.2))
    request.addfinalizer(functools.partial(port_finalizer, worker))
    return True


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def port_with_get_event_loop_finalizer(request):
    def port_finalizer(finalizer):
        async def port_afinalizer():
            # await task using current loop retrieved from the event loop policy
            # RuntimeError is raised if task is created on a different loop.
            # This can happen when pytest_fixture_setup
            # does not set up the loop correctly,
            # for example when policy.set_event_loop() is called with a wrong argument
            await finalizer

        current_loop = asyncio.get_event_loop_policy().get_event_loop()
        current_loop.run_until_complete(port_afinalizer())

    worker = asyncio.ensure_future(asyncio.sleep(0.2))
    request.addfinalizer(functools.partial(port_finalizer, worker))
    return True
