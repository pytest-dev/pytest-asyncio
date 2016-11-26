"""pytest-asyncio implementation."""
import asyncio
import functools
import inspect
import socket

from concurrent.futures import ProcessPoolExecutor
from contextlib import closing

import pytest

from _pytest.fixtures import FixtureFunctionMarker
from _pytest.python import transfer_markers



class ForbiddenEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """An event loop policy that raises errors on most operations.

    Operations involving child watchers are permitted."""

    def get_event_loop(self):
        """Not allowed."""
        raise NotImplementedError

    def set_event_loop(self, _):
        """Not allowed."""
        raise NotImplementedError


def _is_coroutine(obj):
    """Check to see if an object is really an asyncio coroutine."""
    return asyncio.iscoroutinefunction(obj) or inspect.isgeneratorfunction(obj)


def pytest_configure(config):
    """Inject documentation."""
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
    """A pytest hook to collect asyncio coroutines."""
    if collector.funcnamefilter(name) and _is_coroutine(obj):
        item = pytest.Function(name, parent=collector)

        # Due to how pytest test collection works, module-level pytestmarks
        # are applied after the collection step. Since this is the collection
        # step, we look ourselves.
        transfer_markers(obj, item.cls, item.module)
        item = pytest.Function(name, parent=collector)  # To reload keywords.

        if ('asyncio' in item.keywords or
            'asyncio_process_pool' in item.keywords):
            return list(collector._genfunctions(name, obj))


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Adjust the event loop policy when an event loop is produced."""
    outcome = yield

    if fixturedef.argname == "event_loop" and 'asyncio' in request.keywords:
        loop = outcome.get_result()
        for kw in _markers_2_fixtures.keys():
            if kw not in request.keywords:
                continue
            forbid_global_loop = (request.keywords[kw].kwargs
                                  .get('forbid_global_loop', False))

            policy = asyncio.get_event_loop_policy()
            if forbid_global_loop:
                asyncio.set_event_loop_policy(ForbiddenEventLoopPolicy())
                asyncio.get_child_watcher().attach_loop(loop)
                fixturedef.addfinalizer(lambda: asyncio.set_event_loop_policy(policy))
            else:
                policy.set_event_loop(loop)

    return outcome


@pytest.mark.tryfirst
def pytest_pyfunc_call(pyfuncitem):
    """
    Run asyncio marked test functions in an event loop instead of a normal
    function call.
    """
    for marker_name, fixture_name in _markers_2_fixtures.items():
        if marker_name in pyfuncitem.keywords:
            event_loop = pyfuncitem.funcargs[fixture_name]

            funcargs = pyfuncitem.funcargs
            testargs = {arg: funcargs[arg]
                        for arg in pyfuncitem._fixtureinfo.argnames}
            event_loop.run_until_complete(
                asyncio.async(pyfuncitem.obj(**testargs), loop=event_loop))
            return True


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


@pytest.yield_fixture
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
        """Return an unused port."""
        port = unused_tcp_port()

        while port in produced:
            port = unused_tcp_port()

        produced.add(port)

        return port
    return factory


class AsyncFixtureFunctionMarker(FixtureFunctionMarker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, coroutine):
        """The parameter is the actual fixture coroutine."""
        if not _is_coroutine(coroutine):
            raise ValueError('Only coroutine functions supported')

        @functools.wraps(coroutine)
        def inner(*args, **kwargs):
            loop = None
            return loop.run_until_complete(coroutine(*args, **kwargs))

        inner._pytestfixturefunction = self
        return inner


def async_fixture(scope='function', params=None, autouse=False, ids=None):
    if callable(scope) and params is None and not autouse:
        # direct invocation
        marker = AsyncFixtureFunctionMarker(
            'function', params, autouse)
        return marker(scope)
    if params is not None and not isinstance(params, (list, tuple)):
        params = list(params)
    return AsyncFixtureFunctionMarker(
        scope, params, autouse, ids=ids)
