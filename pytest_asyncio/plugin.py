"""pytest-asyncio implementation."""
import asyncio
import contextlib
import enum
import functools
import inspect
import socket
import warnings
from textwrap import dedent
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Set,
    TypeVar,
    Union,
    overload,
)

import pytest
from _pytest.mark.structures import get_unpacked_marks
from pytest import (
    Collector,
    Config,
    FixtureRequest,
    Function,
    Item,
    Metafunc,
    Parser,
    PytestCollectionWarning,
    PytestDeprecationWarning,
    PytestPluginManager,
    Session,
    StashKey,
)

_R = TypeVar("_R")

_ScopeName = Literal["session", "package", "module", "class", "function"]
_T = TypeVar("_T")

SimpleFixtureFunction = TypeVar(
    "SimpleFixtureFunction", bound=Callable[..., Awaitable[_R]]
)
FactoryFixtureFunction = TypeVar(
    "FactoryFixtureFunction", bound=Callable[..., AsyncIterator[_R]]
)
FixtureFunction = Union[SimpleFixtureFunction, FactoryFixtureFunction]
FixtureFunctionMarker = Callable[[FixtureFunction], FixtureFunction]

# https://github.com/pytest-dev/pytest/pull/9510
FixtureDef = Any
SubRequest = Any


class PytestAsyncioError(Exception):
    """Base class for exceptions raised by pytest-asyncio"""


class MultipleEventLoopsRequestedError(PytestAsyncioError):
    """Raised when a test requests multiple asyncio event loops."""


class Mode(str, enum.Enum):
    AUTO = "auto"
    STRICT = "strict"


ASYNCIO_MODE_HELP = """\
'auto' - for automatically handling all async functions by the plugin
'strict' - for autoprocessing disabling (useful if different async frameworks \
should be tested together, e.g. \
both pytest-asyncio and pytest-trio are used in the same project)
"""


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
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
        default="strict",
    )


@overload
def fixture(
    fixture_function: FixtureFunction,
    *,
    scope: "Union[_ScopeName, Callable[[str, Config], _ScopeName]]" = ...,
    params: Optional[Iterable[object]] = ...,
    autouse: bool = ...,
    ids: Union[
        Iterable[Union[str, float, int, bool, None]],
        Callable[[Any], Optional[object]],
        None,
    ] = ...,
    name: Optional[str] = ...,
) -> FixtureFunction:
    ...


@overload
def fixture(
    fixture_function: None = ...,
    *,
    scope: "Union[_ScopeName, Callable[[str, Config], _ScopeName]]" = ...,
    params: Optional[Iterable[object]] = ...,
    autouse: bool = ...,
    ids: Union[
        Iterable[Union[str, float, int, bool, None]],
        Callable[[Any], Optional[object]],
        None,
    ] = ...,
    name: Optional[str] = None,
) -> FixtureFunctionMarker:
    ...


def fixture(
    fixture_function: Optional[FixtureFunction] = None, **kwargs: Any
) -> Union[FixtureFunction, FixtureFunctionMarker]:
    if fixture_function is not None:
        _make_asyncio_fixture_function(fixture_function)
        return pytest.fixture(fixture_function, **kwargs)

    else:

        @functools.wraps(fixture)
        def inner(fixture_function: FixtureFunction) -> FixtureFunction:
            return fixture(fixture_function, **kwargs)

        return inner


def _is_asyncio_fixture_function(obj: Any) -> bool:
    obj = getattr(obj, "__func__", obj)  # instance method maybe?
    return getattr(obj, "_force_asyncio_fixture", False)


def _make_asyncio_fixture_function(obj: Any) -> None:
    if hasattr(obj, "__func__"):
        # instance method, check the function object
        obj = obj.__func__
    obj._force_asyncio_fixture = True


def _is_coroutine_or_asyncgen(obj: Any) -> bool:
    return asyncio.iscoroutinefunction(obj) or inspect.isasyncgenfunction(obj)


def _get_asyncio_mode(config: Config) -> Mode:
    val = config.getoption("asyncio_mode")
    if val is None:
        val = config.getini("asyncio_mode")
    try:
        return Mode(val)
    except ValueError:
        modes = ", ".join(m.value for m in Mode)
        raise pytest.UsageError(
            f"{val!r} is not a valid asyncio_mode. Valid modes: {modes}."
        )


def pytest_configure(config: Config) -> None:
    """Inject documentation."""
    config.addinivalue_line(
        "markers",
        "asyncio: "
        "mark the test as a coroutine, it will be "
        "run using an asyncio event loop",
    )
    config.addinivalue_line(
        "markers",
        "asyncio_event_loop: "
        "Provides an asyncio event loop in the scope of the marked test "
        "class or module",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_report_header(config: Config) -> List[str]:
    """Add asyncio config to pytest header."""
    mode = _get_asyncio_mode(config)
    return [f"asyncio: mode={mode}"]


def _preprocess_async_fixtures(
    collector: Collector,
    processed_fixturedefs: Set[FixtureDef],
) -> None:
    config = collector.config
    asyncio_mode = _get_asyncio_mode(config)
    fixturemanager = config.pluginmanager.get_plugin("funcmanage")
    event_loop_fixture_id = "event_loop"
    for node, mark in collector.iter_markers_with_node("asyncio_event_loop"):
        event_loop_fixture_id = node.stash.get(_event_loop_fixture_id, None)
        if event_loop_fixture_id:
            break
    for fixtures in fixturemanager._arg2fixturedefs.values():
        for fixturedef in fixtures:
            func = fixturedef.func
            if fixturedef in processed_fixturedefs or not _is_coroutine_or_asyncgen(
                func
            ):
                continue
            if not _is_asyncio_fixture_function(func) and asyncio_mode == Mode.STRICT:
                # Ignore async fixtures without explicit asyncio mark in strict mode
                # This applies to pytest_trio fixtures, for example
                continue
            _make_asyncio_fixture_function(func)
            function_signature = inspect.signature(func)
            if "event_loop" in function_signature.parameters:
                warnings.warn(
                    PytestDeprecationWarning(
                        f"{func.__name__} is asynchronous and explicitly "
                        f'requests the "event_loop" fixture. Asynchronous fixtures and '
                        f'test functions should use "asyncio.get_running_loop()" '
                        f"instead."
                    )
                )
            _inject_fixture_argnames(fixturedef, event_loop_fixture_id)
            _synchronize_async_fixture(fixturedef, event_loop_fixture_id)
            assert _is_asyncio_fixture_function(fixturedef.func)
            processed_fixturedefs.add(fixturedef)


def _inject_fixture_argnames(
    fixturedef: FixtureDef, event_loop_fixture_id: str
) -> None:
    """
    Ensures that `request` and `event_loop` are arguments of the specified fixture.
    """
    to_add = []
    for name in ("request", event_loop_fixture_id):
        if name not in fixturedef.argnames:
            to_add.append(name)
    if to_add:
        fixturedef.argnames += tuple(to_add)


def _synchronize_async_fixture(
    fixturedef: FixtureDef, event_loop_fixture_id: str
) -> None:
    """
    Wraps the fixture function of an async fixture in a synchronous function.
    """
    if inspect.isasyncgenfunction(fixturedef.func):
        _wrap_asyncgen_fixture(fixturedef, event_loop_fixture_id)
    elif inspect.iscoroutinefunction(fixturedef.func):
        _wrap_async_fixture(fixturedef, event_loop_fixture_id)


def _add_kwargs(
    func: Callable[..., Any],
    kwargs: Dict[str, Any],
    event_loop_fixture_id: str,
    event_loop: asyncio.AbstractEventLoop,
    request: SubRequest,
) -> Dict[str, Any]:
    sig = inspect.signature(func)
    ret = kwargs.copy()
    if "request" in sig.parameters:
        ret["request"] = request
    if event_loop_fixture_id in sig.parameters:
        ret[event_loop_fixture_id] = event_loop
    return ret


def _perhaps_rebind_fixture_func(
    func: _T, instance: Optional[Any], unittest: bool
) -> _T:
    if instance is not None:
        # The fixture needs to be bound to the actual request.instance
        # so it is bound to the same object as the test method.
        unbound, cls = func, None
        try:
            unbound, cls = func.__func__, type(func.__self__)  # type: ignore
        except AttributeError:
            pass
        # If unittest is true, the fixture is bound unconditionally.
        # otherwise, only if the fixture was bound before to an instance of
        # the same type.
        if unittest or (cls is not None and isinstance(instance, cls)):
            func = unbound.__get__(instance)  # type: ignore
    return func


def _wrap_asyncgen_fixture(fixturedef: FixtureDef, event_loop_fixture_id: str) -> None:
    fixture = fixturedef.func

    @functools.wraps(fixture)
    def _asyncgen_fixture_wrapper(request: SubRequest, **kwargs: Any):
        func = _perhaps_rebind_fixture_func(
            fixture, request.instance, fixturedef.unittest
        )
        event_loop = kwargs.pop(event_loop_fixture_id)
        gen_obj = func(
            **_add_kwargs(func, kwargs, event_loop_fixture_id, event_loop, request)
        )

        async def setup():
            res = await gen_obj.__anext__()
            return res

        def finalizer() -> None:
            """Yield again, to finalize."""

            async def async_finalizer() -> None:
                try:
                    await gen_obj.__anext__()
                except StopAsyncIteration:
                    pass
                else:
                    msg = "Async generator fixture didn't stop."
                    msg += "Yield only once."
                    raise ValueError(msg)

            event_loop.run_until_complete(async_finalizer())

        result = event_loop.run_until_complete(setup())
        request.addfinalizer(finalizer)
        return result

    fixturedef.func = _asyncgen_fixture_wrapper


def _wrap_async_fixture(fixturedef: FixtureDef, event_loop_fixture_id: str) -> None:
    fixture = fixturedef.func

    @functools.wraps(fixture)
    def _async_fixture_wrapper(request: SubRequest, **kwargs: Any):
        func = _perhaps_rebind_fixture_func(
            fixture, request.instance, fixturedef.unittest
        )
        event_loop = kwargs.pop(event_loop_fixture_id)

        async def setup():
            res = await func(
                **_add_kwargs(func, kwargs, event_loop_fixture_id, event_loop, request)
            )
            return res

        return event_loop.run_until_complete(setup())

    fixturedef.func = _async_fixture_wrapper


class PytestAsyncioFunction(Function):
    """Base class for all test functions managed by pytest-asyncio."""

    @classmethod
    def substitute(cls, item: Function, /) -> Function:
        """
        Returns a PytestAsyncioFunction if there is an implementation that can handle
        the specified function item.

        If no implementation of PytestAsyncioFunction can handle the specified item,
        the item is returned unchanged.
        """
        for subclass in cls.__subclasses__():
            if subclass._can_substitute(item):
                return subclass._from_function(item)
        return item

    @classmethod
    def _from_function(cls, function: Function, /) -> Function:
        """
        Instantiates this specific PytestAsyncioFunction type from the specified
        Function item.
        """
        subclass_instance = cls.from_parent(
            function.parent,
            name=function.name,
            callspec=getattr(function, "callspec", None),
            callobj=function.obj,
            fixtureinfo=function._fixtureinfo,
            keywords=function.keywords,
            originalname=function.originalname,
        )
        subclassed_function_signature = inspect.signature(subclass_instance.obj)
        if "event_loop" in subclassed_function_signature.parameters:
            subclass_instance.warn(
                PytestDeprecationWarning(
                    f"{subclass_instance.name} is asynchronous and explicitly "
                    f'requests the "event_loop" fixture. Asynchronous fixtures and '
                    f'test functions should use "asyncio.get_running_loop()" instead.'
                )
            )
        return subclass_instance

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        """Returns whether the specified function can be replaced by this class"""
        raise NotImplementedError()


class Coroutine(PytestAsyncioFunction):
    """Pytest item created by a coroutine"""

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        func = item.obj
        return asyncio.iscoroutinefunction(func)

    def runtest(self) -> None:
        if self.get_closest_marker("asyncio"):
            self.obj = wrap_in_sync(
                # https://github.com/pytest-dev/pytest-asyncio/issues/596
                self.obj,  # type: ignore[has-type]
            )
        super().runtest()


class AsyncGenerator(PytestAsyncioFunction):
    """Pytest item created by an asynchronous generator"""

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        func = item.obj
        return inspect.isasyncgenfunction(func)

    @classmethod
    def _from_function(cls, function: Function, /) -> Function:
        async_gen_item = super()._from_function(function)
        unsupported_item_type_message = (
            f"Tests based on asynchronous generators are not supported. "
            f"{function.name} will be ignored."
        )
        async_gen_item.warn(PytestCollectionWarning(unsupported_item_type_message))
        async_gen_item.add_marker(
            pytest.mark.xfail(run=False, reason=unsupported_item_type_message)
        )
        return async_gen_item


class AsyncStaticMethod(PytestAsyncioFunction):
    """
    Pytest item that is a coroutine or an asynchronous generator
    decorated with staticmethod
    """

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        func = item.obj
        return isinstance(func, staticmethod) and _is_coroutine_or_asyncgen(
            func.__func__
        )

    def runtest(self) -> None:
        if self.get_closest_marker("asyncio"):
            self.obj = wrap_in_sync(
                # https://github.com/pytest-dev/pytest-asyncio/issues/596
                self.obj,  # type: ignore[has-type]
            )
        super().runtest()


class AsyncHypothesisTest(PytestAsyncioFunction):
    """
    Pytest item that is coroutine or an asynchronous generator decorated by
    @hypothesis.given.
    """

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        func = item.obj
        return getattr(
            func, "is_hypothesis_test", False
        ) and asyncio.iscoroutinefunction(func.hypothesis.inner_test)

    def runtest(self) -> None:
        if self.get_closest_marker("asyncio"):
            self.obj.hypothesis.inner_test = wrap_in_sync(
                self.obj.hypothesis.inner_test,
            )
        super().runtest()


_HOLDER: Set[FixtureDef] = set()


# The function name needs to start with "pytest_"
# see https://github.com/pytest-dev/pytest/issues/11307
@pytest.hookimpl(specname="pytest_pycollect_makeitem", tryfirst=True)
def pytest_pycollect_makeitem_preprocess_async_fixtures(
    collector: Union[pytest.Module, pytest.Class], name: str, obj: object
) -> Union[
    pytest.Item, pytest.Collector, List[Union[pytest.Item, pytest.Collector]], None
]:
    """A pytest hook to collect asyncio coroutines."""
    if not collector.funcnamefilter(name):
        return None
    _preprocess_async_fixtures(collector, _HOLDER)
    return None


# The function name needs to start with "pytest_"
# see https://github.com/pytest-dev/pytest/issues/11307
@pytest.hookimpl(specname="pytest_pycollect_makeitem", hookwrapper=True)
def pytest_pycollect_makeitem_convert_async_functions_to_subclass(
    collector: Union[pytest.Module, pytest.Class], name: str, obj: object
) -> Union[
    pytest.Item, pytest.Collector, List[Union[pytest.Item, pytest.Collector]], None
]:
    """
    Converts coroutines and async generators collected as pytest.Functions
    to AsyncFunction items.
    """
    hook_result = yield
    node_or_list_of_nodes = hook_result.get_result()
    if not node_or_list_of_nodes:
        return
    try:
        node_iterator = iter(node_or_list_of_nodes)
    except TypeError:
        # Treat single node as a single-element iterable
        node_iterator = iter((node_or_list_of_nodes,))
    updated_node_collection = []
    for node in node_iterator:
        updated_item = node
        if isinstance(node, Function):
            updated_item = PytestAsyncioFunction.substitute(node)
        updated_node_collection.append(updated_item)

    hook_result.force_result(updated_node_collection)


_event_loop_fixture_id = StashKey[str]


@pytest.hookimpl
def pytest_collectstart(collector: pytest.Collector):
    if not isinstance(collector, (pytest.Class, pytest.Module)):
        return
    # pytest.Collector.own_markers is empty at this point,
    # so we rely on _pytest.mark.structures.get_unpacked_marks
    marks = get_unpacked_marks(collector.obj, consider_mro=True)
    for mark in marks:
        if not mark.name == "asyncio_event_loop":
            continue
        event_loop_policy = mark.kwargs.get("policy", asyncio.get_event_loop_policy())
        policy_params = (
            event_loop_policy
            if isinstance(event_loop_policy, Iterable)
            else (event_loop_policy,)
        )

        # There seem to be issues when a fixture is shadowed by another fixture
        # and both differ in their params.
        # https://github.com/pytest-dev/pytest/issues/2043
        # https://github.com/pytest-dev/pytest/issues/11350
        # As such, we assign a unique name for each event_loop fixture.
        # The fixture name is stored in the collector's Stash, so it can
        # be injected when setting up the test
        event_loop_fixture_id = f"{collector.nodeid}::<event_loop>"
        collector.stash[_event_loop_fixture_id] = event_loop_fixture_id

        @pytest.fixture(
            scope="class" if isinstance(collector, pytest.Class) else "module",
            name=event_loop_fixture_id,
            params=policy_params,
            ids=tuple(type(policy).__name__ for policy in policy_params),
        )
        def scoped_event_loop(
            *args,  # Function needs to accept "cls" when collected by pytest.Class
            request,
        ) -> Iterator[asyncio.AbstractEventLoop]:
            new_loop_policy = request.param
            old_loop_policy = asyncio.get_event_loop_policy()
            old_loop = asyncio.get_event_loop()
            asyncio.set_event_loop_policy(new_loop_policy)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            yield loop
            loop.close()
            asyncio.set_event_loop_policy(old_loop_policy)
            asyncio.set_event_loop(old_loop)

        # @pytest.fixture does not register the fixture anywhere, so pytest doesn't
        # know it exists. We work around this by attaching the fixture function to the
        # collected Python class, where it will be picked up by pytest.Class.collect()
        # or pytest.Module.collect(), respectively
        collector.obj.__pytest_asyncio_scoped_event_loop = scoped_event_loop
        break


def pytest_collection_modifyitems(
    session: Session, config: Config, items: List[Item]
) -> None:
    """
    Marks collected async test items as `asyncio` tests.

    The mark is only applied in `AUTO` mode. It is applied to:

      - coroutines and async generators
      - Hypothesis tests wrapping coroutines
      - staticmethods wrapping coroutines

    """
    if _get_asyncio_mode(config) != Mode.AUTO:
        return
    for item in items:
        if isinstance(item, PytestAsyncioFunction):
            item.add_marker("asyncio")


_REDEFINED_EVENT_LOOP_FIXTURE_WARNING = dedent(
    """\
    The event_loop fixture provided by pytest-asyncio has been redefined in
    %s:%d
    Replacing the event_loop fixture with a custom implementation is deprecated
    and will lead to errors in the future.
    If you want to request an asyncio event loop with a class or module scope,
    please attach the asyncio_event_loop mark to the respective class or module.
    """
)


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc: Metafunc) -> None:
    for event_loop_provider_node, _ in metafunc.definition.iter_markers_with_node(
        "asyncio_event_loop"
    ):
        event_loop_fixture_id = event_loop_provider_node.stash.get(
            _event_loop_fixture_id, None
        )
        if event_loop_fixture_id:
            # This specific fixture name may already be in metafunc.argnames, if this
            # test indirectly depends on the fixture. For example, this is the case
            # when the test depends on an async fixture, both of which share the same
            # asyncio_event_loop mark.
            if event_loop_fixture_id in metafunc.fixturenames:
                continue
            fixturemanager = metafunc.config.pluginmanager.get_plugin("funcmanage")
            if "event_loop" in metafunc.fixturenames:
                raise MultipleEventLoopsRequestedError(
                    _MULTIPLE_LOOPS_REQUESTED_ERROR
                    % (metafunc.definition.nodeid, event_loop_provider_node.nodeid),
                )
            # Add the scoped event loop fixture to Metafunc's list of fixture names and
            # fixturedefs and leave the actual parametrization to pytest
            metafunc.fixturenames.insert(0, event_loop_fixture_id)
            metafunc._arg2fixturedefs[
                event_loop_fixture_id
            ] = fixturemanager._arg2fixturedefs[event_loop_fixture_id]
            break


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(
    fixturedef: FixtureDef, request: SubRequest
) -> Optional[object]:
    """Adjust the event loop policy when an event loop is produced."""
    if fixturedef.argname == "event_loop":
        # The use of a fixture finalizer is preferred over the
        # pytest_fixture_post_finalizer hook. The fixture finalizer is invoked once
        # for each fixture, whereas the hook may be invoked multiple times for
        # any specific fixture.
        # see https://github.com/pytest-dev/pytest/issues/5848
        _add_finalizers(
            fixturedef,
            _close_event_loop,
            _provide_clean_event_loop,
        )
        outcome = yield
        loop = outcome.get_result()
        # Weird behavior was observed when checking for an attribute of FixtureDef.func
        # Instead, we now check for a special attribute of the returned event loop
        fixture_filename = inspect.getsourcefile(fixturedef.func)
        if not getattr(loop, "__original_fixture_loop", False):
            _, fixture_line_number = inspect.getsourcelines(fixturedef.func)
            warnings.warn(
                _REDEFINED_EVENT_LOOP_FIXTURE_WARNING
                % (fixture_filename, fixture_line_number),
                DeprecationWarning,
            )
        policy = asyncio.get_event_loop_policy()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                old_loop = policy.get_event_loop()
            if old_loop is not loop:
                old_loop.close()
        except RuntimeError:
            # Either the current event loop has been set to None
            # or the loop policy doesn't specify to create new loops
            # or we're not in the main thread
            pass
        policy.set_event_loop(loop)
        return

    yield


def _add_finalizers(fixturedef: FixtureDef, *finalizers: Callable[[], object]) -> None:
    """
    Regsiters the specified fixture finalizers in the fixture.

    Finalizers need to specified in the exact order in which they should be invoked.

    :param fixturedef: Fixture definition which finalizers should be added to
    :param finalizers: Finalizers to be added
    """
    for finalizer in reversed(finalizers):
        fixturedef.addfinalizer(finalizer)


_UNCLOSED_EVENT_LOOP_WARNING = dedent(
    """\
    pytest-asyncio detected an unclosed event loop when tearing down the event_loop
    fixture: %r
    pytest-asyncio will close the event loop for you, but future versions of the
    library will no longer do so. In order to ensure compatibility with future
    versions, please make sure that:
        1. Any custom "event_loop" fixture properly closes the loop after yielding it
        2. The scopes of your custom "event_loop" fixtures do not overlap
        3. Your code does not modify the event loop in async fixtures or tests
    """
)


def _close_event_loop() -> None:
    policy = asyncio.get_event_loop_policy()
    try:
        loop = policy.get_event_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        if not loop.is_closed():
            warnings.warn(
                _UNCLOSED_EVENT_LOOP_WARNING % loop,
                DeprecationWarning,
            )
        loop.close()


def _provide_clean_event_loop() -> None:
    # At this point, the event loop for the current thread is closed.
    # When a user calls asyncio.get_event_loop(), they will get a closed loop.
    # In order to avoid this side effect from pytest-asyncio, we need to replace
    # the current loop with a fresh one.
    # Note that we cannot set the loop to None, because get_event_loop only creates
    # a new loop, when set_event_loop has not been called.
    policy = asyncio.get_event_loop_policy()
    new_loop = policy.new_event_loop()
    policy.set_event_loop(new_loop)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: Function) -> Optional[object]:
    """
    Pytest hook called before a test case is run.

    Wraps marked tests in a synchronous function
    where the wrapped test coroutine is executed in an event loop.
    """
    if pyfuncitem.get_closest_marker("asyncio") is not None:
        if isinstance(pyfuncitem, PytestAsyncioFunction):
            pass
        else:
            pyfuncitem.warn(
                pytest.PytestWarning(
                    f"The test {pyfuncitem} is marked with '@pytest.mark.asyncio' "
                    "but it is not an async function. "
                    "Please remove the asyncio mark. "
                    "If the test is not marked explicitly, "
                    "check for global marks applied via 'pytestmark'."
                )
            )
    yield


def wrap_in_sync(
    func: Callable[..., Awaitable[Any]],
):
    """Return a sync wrapper around an async function executing it in the
    current event loop."""

    # if the function is already wrapped, we rewrap using the original one
    # not using __wrapped__ because the original function may already be
    # a wrapped one
    raw_func = getattr(func, "_raw_test_func", None)
    if raw_func is not None:
        func = raw_func

    @functools.wraps(func)
    def inner(*args, **kwargs):
        coro = func(*args, **kwargs)
        _loop = asyncio.get_event_loop()
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

    inner._raw_test_func = func  # type: ignore[attr-defined]
    return inner


_MULTIPLE_LOOPS_REQUESTED_ERROR = dedent(
    """\
        Multiple asyncio event loops with different scopes have been requested
        by %s. The test explicitly requests the event_loop fixture, while another
        event loop is provided by %s.
        Remove "event_loop" from the requested fixture in your test to run the test
        in a larger-scoped event loop or remove the "asyncio_event_loop" mark to run
        the test in a function-scoped event loop.
    """
)


def pytest_runtest_setup(item: pytest.Item) -> None:
    marker = item.get_closest_marker("asyncio")
    if marker is None:
        return
    event_loop_fixture_id = "event_loop"
    for node, mark in item.iter_markers_with_node("asyncio_event_loop"):
        event_loop_fixture_id = node.stash.get(_event_loop_fixture_id, None)
        if event_loop_fixture_id:
            break
    fixturenames = item.fixturenames  # type: ignore[attr-defined]
    # inject an event loop fixture for all async tests
    if "event_loop" in fixturenames:
        fixturenames.remove("event_loop")
    fixturenames.insert(0, event_loop_fixture_id)
    obj = getattr(item, "obj", None)
    if not getattr(obj, "hypothesis", False) and getattr(
        obj, "is_hypothesis_test", False
    ):
        pytest.fail(
            "test function `%r` is using Hypothesis, but pytest-asyncio "
            "only works with Hypothesis 3.64.0 or later." % item
        )


@pytest.fixture
def event_loop(request: FixtureRequest) -> Iterator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    # Add a magic value to the event loop, so pytest-asyncio can determine if the
    # event_loop fixture was overridden. Other implementations of event_loop don't
    # set this value.
    # The magic value must be set as part of the function definition, because pytest
    # seems to have multiple instances of the same FixtureDef or fixture function
    loop.__original_fixture_loop = True  # type: ignore[attr-defined]
    yield loop
    loop.close()


def _unused_port(socket_type: int) -> int:
    """Find an unused localhost port from 1024-65535 and return it."""
    with contextlib.closing(socket.socket(type=socket_type)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def unused_tcp_port() -> int:
    return _unused_port(socket.SOCK_STREAM)


@pytest.fixture
def unused_udp_port() -> int:
    return _unused_port(socket.SOCK_DGRAM)


@pytest.fixture(scope="session")
def unused_tcp_port_factory() -> Callable[[], int]:
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
def unused_udp_port_factory() -> Callable[[], int]:
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
