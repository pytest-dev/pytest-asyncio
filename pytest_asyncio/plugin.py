"""pytest-asyncio implementation."""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import enum
import functools
import inspect
import socket
import sys
import warnings
from asyncio import AbstractEventLoop, AbstractEventLoopPolicy
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Coroutine as AbstractCoroutine,
    Generator,
    Iterable,
    Iterator,
    Sequence,
)
from typing import (
    Any,
    Callable,
    Literal,
    TypeVar,
    Union,
    cast,
    overload,
)

import pluggy
import pytest
from _pytest.scope import Scope
from pytest import (
    Collector,
    Config,
    FixtureDef,
    FixtureRequest,
    Function,
    Item,
    Mark,
    Metafunc,
    Parser,
    PytestCollectionWarning,
    PytestDeprecationWarning,
    PytestPluginManager,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


_ScopeName = Literal["session", "package", "module", "class", "function"]
_T = TypeVar("_T")
_R = TypeVar("_R", bound=Union[Awaitable[Any], AsyncIterator[Any]])
_P = ParamSpec("_P")
FixtureFunction = Callable[_P, _R]


class PytestAsyncioError(Exception):
    """Base class for exceptions raised by pytest-asyncio"""


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
    parser.addini(
        "asyncio_default_fixture_loop_scope",
        type="string",
        help="default scope of the asyncio event loop used to execute async fixtures",
        default=None,
    )
    parser.addini(
        "asyncio_default_test_loop_scope",
        type="string",
        help="default scope of the asyncio event loop used to execute tests",
        default="function",
    )


@overload
def fixture(
    fixture_function: FixtureFunction[_P, _R],
    *,
    scope: _ScopeName | Callable[[str, Config], _ScopeName] = ...,
    loop_scope: _ScopeName | None = ...,
    params: Iterable[object] | None = ...,
    autouse: bool = ...,
    ids: (
        Iterable[str | float | int | bool | None]
        | Callable[[Any], object | None]
        | None
    ) = ...,
    name: str | None = ...,
) -> FixtureFunction[_P, _R]: ...


@overload
def fixture(
    fixture_function: None = ...,
    *,
    scope: _ScopeName | Callable[[str, Config], _ScopeName] = ...,
    loop_scope: _ScopeName | None = ...,
    params: Iterable[object] | None = ...,
    autouse: bool = ...,
    ids: (
        Iterable[str | float | int | bool | None]
        | Callable[[Any], object | None]
        | None
    ) = ...,
    name: str | None = None,
) -> Callable[[FixtureFunction[_P, _R]], FixtureFunction[_P, _R]]: ...


def fixture(
    fixture_function: FixtureFunction[_P, _R] | None = None,
    loop_scope: _ScopeName | None = None,
    **kwargs: Any,
) -> (
    FixtureFunction[_P, _R]
    | Callable[[FixtureFunction[_P, _R]], FixtureFunction[_P, _R]]
):
    if fixture_function is not None:
        _make_asyncio_fixture_function(fixture_function, loop_scope)
        return pytest.fixture(fixture_function, **kwargs)

    else:

        @functools.wraps(fixture)
        def inner(fixture_function: FixtureFunction[_P, _R]) -> FixtureFunction[_P, _R]:
            return fixture(fixture_function, loop_scope=loop_scope, **kwargs)

        return inner


def _is_asyncio_fixture_function(obj: Any) -> bool:
    obj = getattr(obj, "__func__", obj)  # instance method maybe?
    return getattr(obj, "_force_asyncio_fixture", False)


def _make_asyncio_fixture_function(obj: Any, loop_scope: _ScopeName | None) -> None:
    if hasattr(obj, "__func__"):
        # instance method, check the function object
        obj = obj.__func__
    obj._force_asyncio_fixture = True
    obj._loop_scope = loop_scope


def _is_coroutine_or_asyncgen(obj: Any) -> bool:
    return inspect.iscoroutinefunction(obj) or inspect.isasyncgenfunction(obj)


def _get_asyncio_mode(config: Config) -> Mode:
    val = config.getoption("asyncio_mode")
    if val is None:
        val = config.getini("asyncio_mode")
    try:
        return Mode(val)
    except ValueError as e:
        modes = ", ".join(m.value for m in Mode)
        raise pytest.UsageError(
            f"{val!r} is not a valid asyncio_mode. Valid modes: {modes}."
        ) from e


_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET = """\
The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching \
scope. Future versions of pytest-asyncio will default the loop scope for asynchronous \
fixtures to function scope. Set the default fixture loop scope explicitly in order to \
avoid unexpected behavior in the future. Valid fixture loop scopes are: \
"function", "class", "module", "package", "session"
"""


def pytest_configure(config: Config) -> None:
    default_loop_scope = config.getini("asyncio_default_fixture_loop_scope")
    if not default_loop_scope:
        warnings.warn(PytestDeprecationWarning(_DEFAULT_FIXTURE_LOOP_SCOPE_UNSET))
    config.addinivalue_line(
        "markers",
        "asyncio: "
        "mark the test as a coroutine, it will be "
        "run using an asyncio event loop",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_report_header(config: Config) -> list[str]:
    """Add asyncio config to pytest header."""
    mode = _get_asyncio_mode(config)
    default_fixture_loop_scope = config.getini("asyncio_default_fixture_loop_scope")
    default_test_loop_scope = _get_default_test_loop_scope(config)
    header = [
        f"mode={mode}",
        f"asyncio_default_fixture_loop_scope={default_fixture_loop_scope}",
        f"asyncio_default_test_loop_scope={default_test_loop_scope}",
    ]
    return [
        "asyncio: " + ", ".join(header),
    ]


def _preprocess_async_fixtures(
    collector: Collector,
    processed_fixturedefs: set[FixtureDef],
) -> None:
    config = collector.config
    default_loop_scope = config.getini("asyncio_default_fixture_loop_scope")
    asyncio_mode = _get_asyncio_mode(config)
    fixturemanager = config.pluginmanager.get_plugin("funcmanage")
    assert fixturemanager is not None
    for fixtures in fixturemanager._arg2fixturedefs.values():
        for fixturedef in fixtures:
            func = fixturedef.func
            if fixturedef in processed_fixturedefs or not _is_coroutine_or_asyncgen(
                func
            ):
                continue
            if asyncio_mode == Mode.STRICT and not _is_asyncio_fixture_function(func):
                # Ignore async fixtures without explicit asyncio mark in strict mode
                # This applies to pytest_trio fixtures, for example
                continue
            loop_scope = (
                getattr(func, "_loop_scope", None)
                or default_loop_scope
                or fixturedef.scope
            )
            _make_asyncio_fixture_function(func, loop_scope)
            if "request" not in fixturedef.argnames:
                fixturedef.argnames += ("request",)
            _synchronize_async_fixture(fixturedef)
            assert _is_asyncio_fixture_function(fixturedef.func)
            processed_fixturedefs.add(fixturedef)


def _synchronize_async_fixture(fixturedef: FixtureDef) -> None:
    """Wraps the fixture function of an async fixture in a synchronous function."""
    if inspect.isasyncgenfunction(fixturedef.func):
        _wrap_asyncgen_fixture(fixturedef)
    elif inspect.iscoroutinefunction(fixturedef.func):
        _wrap_async_fixture(fixturedef)


def _add_kwargs(
    func: Callable[..., Any],
    kwargs: dict[str, Any],
    request: FixtureRequest,
) -> dict[str, Any]:
    sig = inspect.signature(func)
    ret = kwargs.copy()
    if "request" in sig.parameters:
        ret["request"] = request
    return ret


def _perhaps_rebind_fixture_func(func: _T, instance: Any | None) -> _T:
    if instance is not None:
        # The fixture needs to be bound to the actual request.instance
        # so it is bound to the same object as the test method.
        unbound, cls = func, None
        try:
            unbound, cls = func.__func__, type(func.__self__)  # type: ignore
        except AttributeError:
            pass
        # Only if the fixture was bound before to an instance of
        # the same type.
        if cls is not None and isinstance(instance, cls):
            func = unbound.__get__(instance)  # type: ignore
    return func


def _wrap_asyncgen_fixture(fixturedef: FixtureDef) -> None:
    fixture = fixturedef.func

    @functools.wraps(fixture)
    def _asyncgen_fixture_wrapper(request: FixtureRequest, **kwargs: Any):
        func = _perhaps_rebind_fixture_func(fixture, request.instance)
        event_loop_fixture_id = _get_event_loop_fixture_id_for_async_fixture(
            request, func
        )
        event_loop = request.getfixturevalue(event_loop_fixture_id)
        kwargs.pop(event_loop_fixture_id, None)
        gen_obj = func(**_add_kwargs(func, kwargs, request))

        async def setup():
            res = await gen_obj.__anext__()  # type: ignore[union-attr]
            return res

        context = contextvars.copy_context()
        setup_task = _create_task_in_context(event_loop, setup(), context)
        result = event_loop.run_until_complete(setup_task)

        reset_contextvars = _apply_contextvar_changes(context)

        def finalizer() -> None:
            """Yield again, to finalize."""

            async def async_finalizer() -> None:
                try:
                    await gen_obj.__anext__()  # type: ignore[union-attr]
                except StopAsyncIteration:
                    pass
                else:
                    msg = "Async generator fixture didn't stop."
                    msg += "Yield only once."
                    raise ValueError(msg)

            task = _create_task_in_context(event_loop, async_finalizer(), context)
            event_loop.run_until_complete(task)
            if reset_contextvars is not None:
                reset_contextvars()

        request.addfinalizer(finalizer)
        return result

    fixturedef.func = _asyncgen_fixture_wrapper  # type: ignore[misc]


def _wrap_async_fixture(fixturedef: FixtureDef) -> None:
    fixture = fixturedef.func

    @functools.wraps(fixture)
    def _async_fixture_wrapper(request: FixtureRequest, **kwargs: Any):
        func = _perhaps_rebind_fixture_func(fixture, request.instance)
        event_loop_fixture_id = _get_event_loop_fixture_id_for_async_fixture(
            request, func
        )
        event_loop = request.getfixturevalue(event_loop_fixture_id)
        kwargs.pop(event_loop_fixture_id, None)

        async def setup():
            res = await func(**_add_kwargs(func, kwargs, request))
            return res

        context = contextvars.copy_context()
        setup_task = _create_task_in_context(event_loop, setup(), context)
        result = event_loop.run_until_complete(setup_task)

        # Copy the context vars modified by the setup task into the current
        # context, and (if needed) add a finalizer to reset them.
        #
        # Note that this is slightly different from the behavior of a non-async
        # fixture, which would rely on the fixture author to add a finalizer
        # to reset the variables. In this case, the author of the fixture can't
        # write such a finalizer because they have no way to capture the Context
        # in which the setup function was run, so we need to do it for them.
        reset_contextvars = _apply_contextvar_changes(context)
        if reset_contextvars is not None:
            request.addfinalizer(reset_contextvars)

        return result

    fixturedef.func = _async_fixture_wrapper  # type: ignore[misc]


def _get_event_loop_fixture_id_for_async_fixture(
    request: FixtureRequest, func: Any
) -> str:
    default_loop_scope = cast(
        _ScopeName, request.config.getini("asyncio_default_fixture_loop_scope")
    )
    loop_scope = (
        getattr(func, "_loop_scope", None) or default_loop_scope or request.scope
    )
    return f"_{loop_scope}_event_loop"


def _create_task_in_context(
    loop: asyncio.AbstractEventLoop,
    coro: AbstractCoroutine[Any, Any, _T],
    context: contextvars.Context,
) -> asyncio.Task[_T]:
    """
    Return an asyncio task that runs the coro in the specified context,
    if possible.

    This allows fixture setup and teardown to be run as separate asyncio tasks,
    while still being able to use context-manager idioms to maintain context
    variables and make those variables visible to test functions.

    This is only fully supported on Python 3.11 and newer, as it requires
    the API added for https://github.com/python/cpython/issues/91150.
    On earlier versions, the returned task will use the default context instead.
    """
    try:
        return loop.create_task(coro, context=context)
    except TypeError:
        return loop.create_task(coro)


def _apply_contextvar_changes(
    context: contextvars.Context,
) -> Callable[[], None] | None:
    """
    Copy contextvar changes from the given context to the current context.

    If any contextvars were modified by the fixture, return a finalizer that
    will restore them.
    """
    context_tokens = []
    for var in context:
        try:
            if var.get() is context.get(var):
                # This variable is not modified, so leave it as-is.
                continue
        except LookupError:
            # This variable isn't yet set in the current context at all.
            pass
        token = var.set(context.get(var))
        context_tokens.append((var, token))

    if not context_tokens:
        return None

    def restore_contextvars():
        while context_tokens:
            (var, token) = context_tokens.pop()
            var.reset(token)

    return restore_contextvars


class PytestAsyncioFunction(Function):
    """Base class for all test functions managed by pytest-asyncio."""

    @classmethod
    def item_subclass_for(cls, item: Function, /) -> type[PytestAsyncioFunction] | None:
        """
        Returns a subclass of PytestAsyncioFunction if there is a specialized subclass
        for the specified function item.

        Return None if no specialized subclass exists for the specified item.
        """
        for subclass in cls.__subclasses__():
            if subclass._can_substitute(item):
                return subclass
        return None

    @classmethod
    def _from_function(cls, function: Function, /) -> Function:
        """
        Instantiates this specific PytestAsyncioFunction type from the specified
        Function item.
        """
        assert function.get_closest_marker("asyncio")
        subclass_instance = cls.from_parent(
            function.parent,
            name=function.name,
            callspec=getattr(function, "callspec", None),
            callobj=function.obj,
            fixtureinfo=function._fixtureinfo,
            keywords=function.keywords,
            originalname=function.originalname,
        )
        subclass_instance.own_markers = function.own_markers
        assert subclass_instance.own_markers == function.own_markers
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
        return inspect.iscoroutinefunction(func)

    def runtest(self) -> None:
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
        return (
            getattr(func, "is_hypothesis_test", False)  # type: ignore[return-value]
            and getattr(func, "hypothesis", None)
            and inspect.iscoroutinefunction(func.hypothesis.inner_test)
        )

    def runtest(self) -> None:
        self.obj.hypothesis.inner_test = wrap_in_sync(
            self.obj.hypothesis.inner_test,
        )
        super().runtest()


_HOLDER: set[FixtureDef] = set()


# The function name needs to start with "pytest_"
# see https://github.com/pytest-dev/pytest/issues/11307
@pytest.hookimpl(specname="pytest_pycollect_makeitem", tryfirst=True)
def pytest_pycollect_makeitem_preprocess_async_fixtures(
    collector: pytest.Module | pytest.Class, name: str, obj: object
) -> pytest.Item | pytest.Collector | list[pytest.Item | pytest.Collector] | None:
    """A pytest hook to collect asyncio coroutines."""
    if not collector.funcnamefilter(name):
        return None
    _preprocess_async_fixtures(collector, _HOLDER)
    return None


# The function name needs to start with "pytest_"
# see https://github.com/pytest-dev/pytest/issues/11307
@pytest.hookimpl(specname="pytest_pycollect_makeitem", hookwrapper=True)
def pytest_pycollect_makeitem_convert_async_functions_to_subclass(
    collector: pytest.Module | pytest.Class, name: str, obj: object
) -> Generator[None, pluggy.Result, None]:
    """
    Converts coroutines and async generators collected as pytest.Functions
    to AsyncFunction items.
    """
    hook_result = yield
    try:
        node_or_list_of_nodes: (
            pytest.Item | pytest.Collector | list[pytest.Item | pytest.Collector] | None
        ) = hook_result.get_result()
    except BaseException as e:
        hook_result.force_exception(e)
        return
    if not node_or_list_of_nodes:
        return
    if isinstance(node_or_list_of_nodes, Sequence):
        node_iterator = iter(node_or_list_of_nodes)
    else:
        # Treat single node as a single-element iterable
        node_iterator = iter((node_or_list_of_nodes,))
    updated_node_collection = []
    for node in node_iterator:
        updated_item = node
        if isinstance(node, Function):
            specialized_item_class = PytestAsyncioFunction.item_subclass_for(node)
            if specialized_item_class:
                if _get_asyncio_mode(
                    node.config
                ) == Mode.AUTO and not node.get_closest_marker("asyncio"):
                    node.add_marker("asyncio")
                if node.get_closest_marker("asyncio"):
                    updated_item = specialized_item_class._from_function(node)
        updated_node_collection.append(updated_item)
    hook_result.force_result(updated_node_collection)


@contextlib.contextmanager
def _temporary_event_loop_policy(policy: AbstractEventLoopPolicy) -> Iterator[None]:
    old_loop_policy = _get_event_loop_policy()
    try:
        old_loop = _get_event_loop_no_warn()
    except RuntimeError:
        old_loop = None
    _set_event_loop_policy(policy)
    try:
        yield
    finally:
        _set_event_loop_policy(old_loop_policy)
        _set_event_loop(old_loop)


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc: Metafunc) -> None:
    marker = metafunc.definition.get_closest_marker("asyncio")
    if not marker:
        return
    default_loop_scope = _get_default_test_loop_scope(metafunc.config)
    loop_scope = _get_marked_loop_scope(marker, default_loop_scope)
    event_loop_fixture_id = f"_{loop_scope}_event_loop"
    # This specific fixture name may already be in metafunc.argnames, if this
    # test indirectly depends on the fixture. For example, this is the case
    # when the test depends on an async fixture, both of which share the same
    # event loop fixture mark.
    if event_loop_fixture_id in metafunc.fixturenames:
        return
    fixturemanager = metafunc.config.pluginmanager.get_plugin("funcmanage")
    assert fixturemanager is not None
    # Add the scoped event loop fixture to Metafunc's list of fixture names and
    # fixturedefs and leave the actual parametrization to pytest
    # The fixture needs to be appended to avoid messing up the fixture evaluation
    # order
    metafunc.fixturenames.append(event_loop_fixture_id)
    metafunc._arg2fixturedefs[event_loop_fixture_id] = fixturemanager._arg2fixturedefs[
        event_loop_fixture_id
    ]


def _get_event_loop_policy() -> AbstractEventLoopPolicy:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return asyncio.get_event_loop_policy()


def _set_event_loop_policy(policy: AbstractEventLoopPolicy) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(policy)


def _get_event_loop_no_warn(
    policy: AbstractEventLoopPolicy | None = None,
) -> asyncio.AbstractEventLoop:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        if policy is not None:
            return policy.get_event_loop()
        else:
            return asyncio.get_event_loop()


def _set_event_loop(loop: AbstractEventLoop | None) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop(loop)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: Function) -> object | None:
    """
    Pytest hook called before a test case is run.

    Wraps marked tests in a synchronous function
    where the wrapped test coroutine is executed in an event loop.
    """
    if pyfuncitem.get_closest_marker("asyncio") is not None:
        if isinstance(pyfuncitem, PytestAsyncioFunction):
            asyncio_mode = _get_asyncio_mode(pyfuncitem.config)
            for fixname, fixtures in pyfuncitem._fixtureinfo.name2fixturedefs.items():
                # name2fixturedefs is a dict between fixture name and a list of matching
                # fixturedefs. The last entry in the list is closest and the one used.
                func = fixtures[-1].func
                if (
                    asyncio_mode == Mode.STRICT
                    and _is_coroutine_or_asyncgen(func)
                    and not _is_asyncio_fixture_function(func)
                ):
                    warnings.warn(
                        PytestDeprecationWarning(
                            f"asyncio test {pyfuncitem.name!r} requested async "
                            "@pytest.fixture "
                            f"{fixname!r} in strict mode. "
                            "You might want to use @pytest_asyncio.fixture or switch "
                            "to auto mode. "
                            "This will become an error in future versions of "
                            "flake8-asyncio."
                        ),
                        stacklevel=1,
                    )
                    # no stacklevel points at the users code, so we set stacklevel=1
                    # so it at least indicates that it's the plugin complaining.
                    # Pytest gives the test file & name in the warnings summary at least

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
    return None


def wrap_in_sync(
    func: Callable[..., Awaitable[Any]],
):
    """
    Return a sync wrapper around an async function executing it in the
    current event loop.
    """
    # if the function is already wrapped, we rewrap using the original one
    # not using __wrapped__ because the original function may already be
    # a wrapped one
    raw_func = getattr(func, "_raw_test_func", None)
    if raw_func is not None:
        func = raw_func

    @functools.wraps(func)
    def inner(*args, **kwargs):
        coro = func(*args, **kwargs)
        _loop = _get_event_loop_no_warn()
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


def pytest_runtest_setup(item: pytest.Item) -> None:
    marker = item.get_closest_marker("asyncio")
    if marker is None:
        return
    default_loop_scope = _get_default_test_loop_scope(item.config)
    loop_scope = _get_marked_loop_scope(marker, default_loop_scope)
    event_loop_fixture_id = f"_{loop_scope}_event_loop"
    fixturenames = item.fixturenames  # type: ignore[attr-defined]
    if event_loop_fixture_id not in fixturenames:
        fixturenames.append(event_loop_fixture_id)
    obj = getattr(item, "obj", None)
    if not getattr(obj, "hypothesis", False) and getattr(
        obj, "is_hypothesis_test", False
    ):
        pytest.fail(
            f"test function `{item!r}` is using Hypothesis, but pytest-asyncio "
            "only works with Hypothesis 3.64.0 or later."
        )


_DUPLICATE_LOOP_SCOPE_DEFINITION_ERROR = """\
An asyncio pytest marker defines both "scope" and "loop_scope", \
but it should only use "loop_scope".
"""

_MARKER_SCOPE_KWARG_DEPRECATION_WARNING = """\
The "scope" keyword argument to the asyncio marker has been deprecated. \
Please use the "loop_scope" argument instead.
"""


def _get_marked_loop_scope(
    asyncio_marker: Mark, default_loop_scope: _ScopeName
) -> _ScopeName:
    assert asyncio_marker.name == "asyncio"
    if asyncio_marker.args or (
        asyncio_marker.kwargs and set(asyncio_marker.kwargs) - {"loop_scope", "scope"}
    ):
        raise ValueError("mark.asyncio accepts only a keyword argument 'loop_scope'.")
    if "scope" in asyncio_marker.kwargs:
        if "loop_scope" in asyncio_marker.kwargs:
            raise pytest.UsageError(_DUPLICATE_LOOP_SCOPE_DEFINITION_ERROR)
        warnings.warn(PytestDeprecationWarning(_MARKER_SCOPE_KWARG_DEPRECATION_WARNING))
    scope = asyncio_marker.kwargs.get("loop_scope") or asyncio_marker.kwargs.get(
        "scope"
    )
    if scope is None:
        scope = default_loop_scope
    assert scope in {"function", "class", "module", "package", "session"}
    return scope


def _get_default_test_loop_scope(config: Config) -> _ScopeName:
    return config.getini("asyncio_default_test_loop_scope")


def _create_scoped_event_loop_fixture(scope: _ScopeName) -> Callable:
    @pytest.fixture(
        scope=scope,
        name=f"_{scope}_event_loop",
    )
    def _scoped_event_loop(
        *args,  # Function needs to accept "cls" when collected by pytest.Class
        event_loop_policy,
    ) -> Iterator[asyncio.AbstractEventLoop]:
        new_loop_policy = event_loop_policy
        with (
            _temporary_event_loop_policy(new_loop_policy),
            _provide_event_loop() as loop,
        ):
            _set_event_loop(loop)
            yield loop

    return _scoped_event_loop


for scope in Scope:
    globals()[f"_{scope.value}_event_loop"] = _create_scoped_event_loop_fixture(
        scope.value
    )


@contextlib.contextmanager
def _provide_event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    policy = _get_event_loop_policy()
    loop = policy.new_event_loop()
    try:
        yield loop
    finally:
        # cleanup the event loop if it hasn't been cleaned up already
        if not loop.is_closed():
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as e:
                warnings.warn(f"Error cleaning up asyncio loop: {e}", RuntimeWarning)
            finally:
                loop.close()


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy() -> AbstractEventLoopPolicy:
    """Return an instance of the policy used to create asyncio event loops."""
    return _get_event_loop_policy()


def is_async_test(item: Item) -> bool:
    """Returns whether a test item is a pytest-asyncio test"""
    return isinstance(item, PytestAsyncioFunction)


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
