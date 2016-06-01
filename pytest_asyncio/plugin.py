import asyncio
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
import inspect
import socket
import pytest


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
        if ('asyncio' in item.keywords or
           'asyncio_process_pool' in item.keywords):
            return list(collector._genfunctions(name, obj))


@pytest.mark.tryfirst
def pytest_pyfunc_call(pyfuncitem):
    """
    Run asyncio marked test functions in an event loop instead of a normal
    function call.
    """
    for marker_name, fixture_name in _markers_2_fixtures.items():
        if marker_name in pyfuncitem.keywords:
            event_loop = pyfuncitem.funcargs[fixture_name]

            forbid_global_loop = pyfuncitem.keywords[marker_name].kwargs.get('forbid_global_loop')

            policy = asyncio.get_event_loop_policy()
            if forbid_global_loop:
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
                if forbid_global_loop:
                    asyncio.set_event_loop_policy(policy)
                event_loop.close()


def pytest_runtest_setup(item):
    for marker, fixture in _markers_2_fixtures.items():
        if marker in item.keywords and fixture not in item.fixturenames:
            # inject an event loop fixture for all async tests
            item.fixturenames.append(fixture)


# maps marker to the name of the event loop fixture that will be available
# to marked test functions
_markers_2_fixtures = {
    'asyncio': 'event_loop',
    'asyncio_process_pool': 'event_loop_process_pool',
}


@pytest.fixture
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    return policy.new_event_loop()


@pytest.fixture
def event_loop_process_pool(event_loop):
    """Create a fresh instance of the default event loop.

    The event loop will have a process pool set as the default executor."""
    event_loop.set_default_executor(ProcessPoolExecutor())
    return event_loop


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
