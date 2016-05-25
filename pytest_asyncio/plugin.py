import asyncio
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import inspect
import socket
import pytest


class MissingLoopFixture(Exception):
    """Raised if a test coroutine function does not request a loop fixture."""
    pass


class ForbiddenEventLoopPolicy(asyncio.AbstractEventLoopPolicy):
    """An event loop policy that raises errors on any operation."""
    pass


def _is_coroutine(obj):
    """Check to see if an object is really an asyncio coroutine."""
    return asyncio.iscoroutinefunction(obj) or inspect.isgeneratorfunction(obj)


def pytest_configure(config):
    config.addinivalue_line("markers",
                            "asyncio: "
                            "mark the test as a coroutine, it will be "
                            "run using an asyncio event loop")
    config.addinivalue_line("markers",
                            "asyncio_process_pool: "
                            "mark the test as a coroutine, it will be "
                            "run using an asyncio event loop with a process "
                            "pool")


@pytest.mark.tryfirst
def pytest_pycollect_makeitem(collector, name, obj):
    if collector.funcnamefilter(name) and _is_coroutine(obj):
        item = pytest.Function(name, parent=collector)
        if 'asyncio' in item.keywords:
            return list(collector._genfunctions(name, obj))


@pytest.mark.tryfirst
def pytest_pyfunc_call(pyfuncitem):
    """
    Run asyncio marked test functions in an event loop instead of a normal
    function call.
    """
    if 'asyncio' in pyfuncitem.keywords:
        marker_kwargs = pyfuncitem.keywords['asyncio'].kwargs
        accept_global_loop = marker_kwargs.get('accept_global_loop', False)

        event_loop = None
        for name, value in pyfuncitem.funcargs.items():
            if isinstance(value, asyncio.AbstractEventLoop):
                event_loop = value
                break
        else:
            if not accept_global_loop:
                raise MissingLoopFixture('A loop fixture must be provided '
                                         'to run test coroutine functions')

        policy = asyncio.get_event_loop_policy()
        current_event_loop = policy.get_event_loop()
        if accept_global_loop and event_loop is None:
            event_loop = current_event_loop

        if not accept_global_loop:
            asyncio.set_event_loop_policy(ForbiddenEventLoopPolicy())
        else:
            policy.set_event_loop(event_loop)


        funcargs = pyfuncitem.funcargs
        testargs = {arg: funcargs[arg]
                    for arg in pyfuncitem._fixtureinfo.argnames}
        try:
            event_loop.run_until_complete(
                asyncio.async(pyfuncitem.obj(**testargs), loop=event_loop))
            return True
        finally:
            if not accept_global_loop:
                asyncio.set_event_loop_policy(policy)


@pytest.fixture
def unused_tcp_port():
    """Find an unused localhost TCP port from 1024-65535 and return it."""
    with closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture
def unused_tcp_port_factory():
    """A factory function, producing different unused TCP ports."""
    produced = set()

    def factory():
        port = unused_tcp_port()

        while port in produced:
            port = unused_tcp_port()

        produced.add(port)

        return port
    return factory
