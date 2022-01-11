"""pytest-asyncio implementation."""
import asyncio
import contextlib
import enum
import functools
import inspect
import socket
import warnings

import pytest


class Mode(str, enum.Enum):
    AUTO = "auto"
    STRICT = "strict"
    LEGACY = "legacy"


LEGACY_MODE = DeprecationWarning(
    "The 'asyncio_mode' default value will change to 'strict' in future, "
    "please explicitly use 'asyncio_mode=strict' or 'asyncio_mode=auto' "
    "in pytest configuration file."
)

LEGACY_ASYNCIO_FIXTURE = (
    "'@pytest.fixture' is applied to {name} "
    "in 'legacy' mode, "
    "please replace it with '@pytest_asyncio.fixture' as a preparation "
    "for switching to 'strict' mode (or use 'auto' mode to seamlessly handle "
    "all these fixtures as asyncio-driven)."
)


ASYNCIO_MODE_HELP = """\
'auto' - for automatically handling all async functions by the plugin
'strict' - for autoprocessing disabling (useful if different async frameworks \
should be tested together, e.g. \
both pytest-asyncio and pytest-trio are used in the same project)
'legacy' - for keeping compatibility with pytest-asyncio<0.17: \
auto-handling is disabled but pytest_asyncio.fixture usage is not enforced
"""


def pytest_addoption(parser, pluginmanager):
    group = parser.getgroup("asyncio")
    group.addoption(
        "--asyncio-mode",
        dest="asyncio_mode",
        default=None,
        metavar="MODE",
        help=ASYNCIO_MODE_HELP,
    )
    parser.addini(
        "asyncio_mode",
        help="default value for --asyncio-mode",
        type="string",
        default="legacy",
    )


def fixture(fixture_function=None, **kwargs):
    if fixture_function is not None:
        _set_explicit_asyncio_mark(fixture_function)
        return pytest.fixture(fixture_function, **kwargs)

    else:

        @functools.wraps(fixture)
        def inner(fixture_function):
            return fixture(fixture_function, **kwargs)

        return inner


def _has_explicit_asyncio_mark(obj):
    obj = getattr(obj, "__func__", obj)  # instance method maybe?
    return getattr(obj, "_force_asyncio_fixture", False)


def _set_explicit_asyncio_mark(obj):
    if hasattr(obj, "__func__"):
        # instance method, check the function object
        obj = obj.__func__
    obj._force_asyncio_fixture = True


def _is_coroutine(obj):
    """Check to see if an object is really an asyncio coroutine."""
    return asyncio.iscoroutinefunction(obj) or inspect.isgeneratorfunction(obj)


def _is_coroutine_or_asyncgen(obj):
    return _is_coroutine(obj) or inspect.isasyncgenfunction(obj)


def _get_asyncio_mode(config):
    val = config.getoption("asyncio_mode")
    if val is None:
        val = config.getini("asyncio_mode")
    return Mode(val)


def pytest_configure(config):
    """Inject documentation."""
    config.addinivalue_line(
        "markers",
        "asyncio: "
        "mark the test as a coroutine, it will be "
        "run using an asyncio event loop",
    )
    if _get_asyncio_mode(config) == Mode.LEGACY:
        config.issue_config_time_warning(LEGACY_MODE, stacklevel=2)


@pytest.mark.tryfirst
def pytest_pycollect_makeitem(collector, name, obj):
    """A pytest hook to collect asyncio coroutines."""
    if collector.funcnamefilter(name) and _is_coroutine(obj):
        item = pytest.Function.from_parent(collector, name=name)
        if "asyncio" in item.keywords:
            return list(collector._genfunctions(name, obj))
        else:
            if _get_asyncio_mode(item.config) == Mode.AUTO:
                # implicitly add asyncio marker if asyncio mode is on
                ret = list(collector._genfunctions(name, obj))
                for elem in ret:
                    elem.add_marker("asyncio")
                return ret


class FixtureStripper:
    """Include additional Fixture, and then strip them"""

    REQUEST = "request"
    EVENT_LOOP = "event_loop"

    def __init__(self, fixturedef):
        self.fixturedef = fixturedef
        self.to_strip = set()

    def add(self, name):
        """Add fixture name to fixturedef
        and record in to_strip list (If not previously included)"""
        if name in self.fixturedef.argnames:
            return
        self.fixturedef.argnames += (name,)
        self.to_strip.add(name)

    def get_and_strip_from(self, name, data_dict):
        """Strip name from data, and return value"""
        result = data_dict[name]
        if name in self.to_strip:
            del data_dict[name]
        return result


@pytest.hookimpl(trylast=True)
def pytest_fixture_post_finalizer(fixturedef, request):
    """Called after fixture teardown"""
    if fixturedef.argname == "event_loop":
        policy = asyncio.get_event_loop_policy()
        # Clean up existing loop to avoid ResourceWarnings
        policy.get_event_loop().close()
        new_loop = policy.new_event_loop()  # Replace existing event loop
        # Ensure subsequent calls to get_event_loop() succeed
        policy.set_event_loop(new_loop)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Adjust the event loop policy when an event loop is produced."""
    if fixturedef.argname == "event_loop":
        outcome = yield
        loop = outcome.get_result()
        policy = asyncio.get_event_loop_policy()
        try:
            old_loop = policy.get_event_loop()
            if old_loop is not loop:
                old_loop.close()
        except RuntimeError:
            # Swallow this, since it's probably bad event loop hygiene.
            pass
        policy.set_event_loop(loop)
        return

    func = fixturedef.func
    if not _is_coroutine_or_asyncgen(func):
        # Nothing to do with a regular fixture function
        yield
        return

    config = request.node.config
    asyncio_mode = _get_asyncio_mode(config)

    if not _has_explicit_asyncio_mark(func):
        if asyncio_mode == Mode.AUTO:
            # Enforce asyncio mode if 'auto'
            _set_explicit_asyncio_mark(func)
        elif asyncio_mode == Mode.LEGACY:
            _set_explicit_asyncio_mark(func)
            try:
                code = func.__code__
            except AttributeError:
                code = func.__func__.__code__
            name = (
                f"<fixture {func.__qualname__}, file={code.co_filename}, "
                f"line={code.co_firstlineno}>"
            )
            warnings.warn(
                LEGACY_ASYNCIO_FIXTURE.format(name=name),
                DeprecationWarning,
            )
        else:
            # asyncio_mode is STRICT,
            # don't handle fixtures that are not explicitly marked
            yield
            return

    if inspect.isasyncgenfunction(func):
        # This is an async generator function. Wrap it accordingly.
        generator = func

        fixture_stripper = FixtureStripper(fixturedef)
        fixture_stripper.add(FixtureStripper.EVENT_LOOP)
        fixture_stripper.add(FixtureStripper.REQUEST)

        def wrapper(*args, **kwargs):
            loop = fixture_stripper.get_and_strip_from(
                FixtureStripper.EVENT_LOOP, kwargs
            )
            request = fixture_stripper.get_and_strip_from(
                FixtureStripper.REQUEST, kwargs
            )

            gen_obj = generator(*args, **kwargs)

            async def setup():
                res = await gen_obj.__anext__()
                return res

            def finalizer():
                """Yield again, to finalize."""

                async def async_finalizer():
                    try:
                        await gen_obj.__anext__()
                    except StopAsyncIteration:
                        pass
                    else:
                        msg = "Async generator fixture didn't stop."
                        msg += "Yield only once."
                        raise ValueError(msg)

                loop.run_until_complete(async_finalizer())

            result = loop.run_until_complete(setup())
            request.addfinalizer(finalizer)
            return result

        fixturedef.func = wrapper
    elif inspect.iscoroutinefunction(func):
        coro = func

        fixture_stripper = FixtureStripper(fixturedef)
        fixture_stripper.add(FixtureStripper.EVENT_LOOP)

        def wrapper(*args, **kwargs):
            loop = fixture_stripper.get_and_strip_from(
                FixtureStripper.EVENT_LOOP, kwargs
            )

            async def setup():
                res = await coro(*args, **kwargs)
                return res

            return loop.run_until_complete(setup())

        fixturedef.func = wrapper
    yield


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    """
    Pytest hook called before a test case is run.

    Wraps marked tests in a synchronous function
    where the wrapped test coroutine is executed in an event loop.
    """
    if "asyncio" in pyfuncitem.keywords:
        if getattr(pyfuncitem.obj, "is_hypothesis_test", False):
            pyfuncitem.obj.hypothesis.inner_test = wrap_in_sync(
                pyfuncitem.obj.hypothesis.inner_test,
                _loop=pyfuncitem.funcargs["event_loop"],
            )
        else:
            pyfuncitem.obj = wrap_in_sync(
                pyfuncitem.obj, _loop=pyfuncitem.funcargs["event_loop"]
            )
    yield


def wrap_in_sync(func, _loop):
    """Return a sync wrapper around an async function executing it in the
    current event loop."""

    # if the function is already wrapped, we rewrap using the original one
    # not using __wrapped__ because the original function may already be
    # a wrapped one
    if hasattr(func, "_raw_test_func"):
        func = func._raw_test_func

    @functools.wraps(func)
    def inner(**kwargs):
        coro = func(**kwargs)
        if coro is not None:
            task = asyncio.ensure_future(coro, loop=_loop)
            try:
                _loop.run_until_complete(task)
            except BaseException:
                # run_until_complete doesn't get the result from exceptions
                # that are not subclasses of `Exception`. Consume all
                # exceptions to prevent asyncio's warning from logging.
                if task.done() and not task.cancelled():
                    task.exception()
                raise

    inner._raw_test_func = func
    return inner


def pytest_runtest_setup(item):
    if "asyncio" in item.keywords:
        # inject an event loop fixture for all async tests
        if "event_loop" in item.fixturenames:
            item.fixturenames.remove("event_loop")
        item.fixturenames.insert(0, "event_loop")
    if (
        item.get_closest_marker("asyncio") is not None
        and not getattr(item.obj, "hypothesis", False)
        and getattr(item.obj, "is_hypothesis_test", False)
    ):
        pytest.fail(
            "test function `%r` is using Hypothesis, but pytest-asyncio "
            "only works with Hypothesis 3.64.0 or later." % item
        )


@pytest.fixture
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def _unused_port(socket_type):
    """Find an unused localhost port from 1024-65535 and return it."""
    with contextlib.closing(socket.socket(type=socket_type)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def unused_tcp_port():
    return _unused_port(socket.SOCK_STREAM)


@pytest.fixture
def unused_udp_port():
    return _unused_port(socket.SOCK_DGRAM)


@pytest.fixture(scope="session")
def unused_tcp_port_factory():
    """A factory function, producing different unused TCP ports."""
    produced = set()

    def factory():
        """Return an unused port."""
        port = _unused_port(socket.SOCK_STREAM)

        while port in produced:
            port = _unused_port(socket.SOCK_STREAM)

        produced.add(port)

        return port

    return factory


@pytest.fixture(scope="session")
def unused_udp_port_factory():
    """A factory function, producing different unused UDP ports."""
    produced = set()

    def factory():
        """Return an unused port."""
        port = _unused_port(socket.SOCK_DGRAM)

        while port in produced:
            port = _unused_port(socket.SOCK_DGRAM)

        produced.add(port)

        return port

    return factory
