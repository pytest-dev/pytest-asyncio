"""The @pytest_asyncio.fixture decorator and the machinery that runs async fixtures."""

from __future__ import annotations

import contextvars
import functools
import inspect
import warnings
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Iterable,
)
from types import AsyncGeneratorType, CoroutineType
from typing import Any, ParamSpec, TypeVar, overload

import pytest
from _pytest.fixtures import resolve_fixture_function
from pytest import (
    Config,
    FixtureDef,
    FixtureRequest,
    MonkeyPatch,
    PytestDeprecationWarning,
)

from . import _runner
from ._collection import _is_coroutine_or_asyncgen
from ._config import Mode, _get_asyncio_mode
from ._hooks import _ScopeName
from ._runner import (
    Runner,
    _EVENT_LOOP_POLICY_FIXTURE_DEPRECATION_WARNING,
    _temporary_event_loop,
)

_R = TypeVar("_R", bound=Awaitable | AsyncIterable | AsyncIterator)
_P = ParamSpec("_P")
FixtureFunction = Callable[_P, _R]


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


def _fixture_synchronizer(
    fixturedef: FixtureDef, runner: Runner, request: FixtureRequest
) -> Callable:
    """Returns a synchronous function evaluating the specified fixture."""
    fixture_function = resolve_fixture_function(fixturedef, request)
    if inspect.isasyncgenfunction(fixturedef.func):
        return _wrap_asyncgen_fixture(fixture_function, runner, request)  # type: ignore[arg-type]
    elif inspect.iscoroutinefunction(fixturedef.func):
        return _wrap_async_fixture(fixture_function, runner, request)  # type: ignore[arg-type]
    elif inspect.isgeneratorfunction(fixturedef.func):
        return _wrap_syncgen_fixture(fixture_function, runner)  # type: ignore[arg-type]
    else:
        return _wrap_sync_fixture(fixture_function, runner)  # type: ignore[arg-type]


SyncGenFixtureParams = ParamSpec("SyncGenFixtureParams")
SyncGenFixtureYieldType = TypeVar("SyncGenFixtureYieldType")


def _wrap_syncgen_fixture(
    fixture_function: Callable[
        SyncGenFixtureParams, Generator[SyncGenFixtureYieldType]
    ],
    runner: Runner,
) -> Callable[SyncGenFixtureParams, Generator[SyncGenFixtureYieldType]]:
    @functools.wraps(fixture_function)
    def _syncgen_fixture_wrapper(
        *args: SyncGenFixtureParams.args,
        **kwargs: SyncGenFixtureParams.kwargs,
    ) -> Generator[SyncGenFixtureYieldType]:
        with _temporary_event_loop(runner.get_loop()):
            yield from fixture_function(*args, **kwargs)

    return _syncgen_fixture_wrapper


SyncFixtureParams = ParamSpec("SyncFixtureParams")
SyncFixtureReturnType = TypeVar("SyncFixtureReturnType")


def _wrap_sync_fixture(
    fixture_function: Callable[SyncFixtureParams, SyncFixtureReturnType],
    runner: Runner,
) -> Callable[SyncFixtureParams, SyncFixtureReturnType]:
    @functools.wraps(fixture_function)
    def _sync_fixture_wrapper(
        *args: SyncFixtureParams.args,
        **kwargs: SyncFixtureParams.kwargs,
    ) -> SyncFixtureReturnType:
        with _temporary_event_loop(runner.get_loop()):
            return fixture_function(*args, **kwargs)

    return _sync_fixture_wrapper


AsyncGenFixtureParams = ParamSpec("AsyncGenFixtureParams")
AsyncGenFixtureYieldType = TypeVar("AsyncGenFixtureYieldType")


def _wrap_asyncgen_fixture(
    fixture_function: Callable[
        AsyncGenFixtureParams, AsyncGeneratorType[AsyncGenFixtureYieldType, Any]
    ],
    runner: Runner,
    request: FixtureRequest,
) -> Callable[AsyncGenFixtureParams, AsyncGenFixtureYieldType]:
    @functools.wraps(fixture_function)
    def _asyncgen_fixture_wrapper(
        *args: AsyncGenFixtureParams.args,
        **kwargs: AsyncGenFixtureParams.kwargs,
    ):
        gen_obj = fixture_function(*args, **kwargs)

        async def setup():
            res = await gen_obj.__anext__()
            return res

        context = contextvars.copy_context()
        result = runner.run(setup(), context=context)

        reset_contextvars = _apply_contextvar_changes(context)

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

            runner.run(async_finalizer(), context=context)
            if reset_contextvars is not None:
                reset_contextvars()

        request.addfinalizer(finalizer)
        return result

    return _asyncgen_fixture_wrapper


AsyncFixtureParams = ParamSpec("AsyncFixtureParams")
AsyncFixtureReturnType = TypeVar("AsyncFixtureReturnType")


def _wrap_async_fixture(
    fixture_function: Callable[
        AsyncFixtureParams, CoroutineType[Any, Any, AsyncFixtureReturnType]
    ],
    runner: Runner,
    request: FixtureRequest,
) -> Callable[AsyncFixtureParams, AsyncFixtureReturnType]:
    @functools.wraps(fixture_function)
    def _async_fixture_wrapper(
        *args: AsyncFixtureParams.args,
        **kwargs: AsyncFixtureParams.kwargs,
    ):
        async def setup():
            res = await fixture_function(*args, **kwargs)
            return res

        context = contextvars.copy_context()
        result = runner.run(setup(), context=context)

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

    return _async_fixture_wrapper


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
            var, token = context_tokens.pop()
            var.reset(token)

    return restore_contextvars


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef: FixtureDef, request) -> object | None:
    if (
        fixturedef.argname == "event_loop_policy"
        and fixturedef.func.__module__ != _runner.__name__
    ):
        warnings.warn(
            PytestDeprecationWarning(_EVENT_LOOP_POLICY_FIXTURE_DEPRECATION_WARNING),
        )
    asyncio_mode = _get_asyncio_mode(request.config)
    if not _is_asyncio_fixture_function(fixturedef.func):
        if asyncio_mode == Mode.STRICT:
            # Ignore async fixtures without explicit asyncio mark in strict mode
            # This applies to pytest_trio fixtures, for example
            return (yield)
        if not _is_coroutine_or_asyncgen(fixturedef.func):
            return (yield)
    default_loop_scope = request.config.getini("asyncio_default_fixture_loop_scope")
    loop_scope = (
        getattr(fixturedef.func, "_loop_scope", None)
        or default_loop_scope
        or fixturedef.scope
    )
    runner_fixture_id = f"_{loop_scope}_scoped_runner"
    runner = request.getfixturevalue(runner_fixture_id)
    # Prevent the runner closing before the fixture's async teardown.
    runner_fixturedef = request._get_active_fixturedef(runner_fixture_id)
    runner_fixturedef.addfinalizer(
        functools.partial(fixturedef.finish, request=request)
    )
    synchronizer = _fixture_synchronizer(fixturedef, runner, request)
    _make_asyncio_fixture_function(synchronizer, loop_scope)
    with MonkeyPatch.context() as c:
        c.setattr(fixturedef, "func", synchronizer)
        hook_result = yield
    return hook_result
