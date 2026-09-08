import asyncio


class FirstLoop(asyncio.SelectorEventLoop):
    pass


class SecondLoop(asyncio.SelectorEventLoop):
    pass


def pytest_asyncio_loop_factories():
    return {"first": FirstLoop, "second": SecondLoop}
