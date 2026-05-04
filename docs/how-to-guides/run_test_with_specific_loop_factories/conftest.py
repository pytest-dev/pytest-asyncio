import asyncio


class CustomEventLoop(asyncio.SelectorEventLoop):
    pass


def pytest_asyncio_loop_factories(config, item):
    return {
        "default": asyncio.new_event_loop,
        "custom": CustomEventLoop,
    }
