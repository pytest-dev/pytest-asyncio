import asyncio

import pytest


class CustomEventLoop(asyncio.SelectorEventLoop):
    pass


@pytest.fixture
def requires_custom_loop():
    pass


def pytest_asyncio_loop_factories(config, item):
    if "requires_custom_loop" in item.fixturenames:
        return {"custom": CustomEventLoop}
    return {"default": asyncio.new_event_loop}
