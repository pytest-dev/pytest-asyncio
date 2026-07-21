"""Collection of asyncio tests: turn collected async functions into runnable items."""

from __future__ import annotations

import contextvars
import functools
import inspect
import sys
from collections.abc import Callable, Collection, Generator, Sequence
from types import CoroutineType

import pluggy
import pytest
from pytest import Function, Item, MonkeyPatch, PytestCollectionWarning

from ._config import _get_default_test_loop_scope
from ._hooks import _ScopeName
from ._markers import (
    _collect_hook_loop_factories,
    _parse_asyncio_marker,
    _resolve_asyncio_marker,
)
from ._runner import _asyncio_loop_factory

if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs


def _is_coroutine_or_asyncgen(obj: object) -> bool:
    return inspect.iscoroutinefunction(obj) or inspect.isasyncgenfunction(obj)


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
        assert function.parent is not None
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

    def setup(self) -> None:
        runner_fixture_id = f"_{self._loop_scope}_scoped_runner"
        if runner_fixture_id not in self.fixturenames:
            self.fixturenames.append(runner_fixture_id)
        # When loop factories are configured, resolve the loop factory
        # fixture early so that a factory variant change cascades cache
        # invalidation before any async fixture checks its cache.
        hook_caller = self.config.hook.pytest_asyncio_loop_factories
        if hook_caller.get_hookimpls():
            _ = self._request.getfixturevalue(_asyncio_loop_factory.__name__)
        return super().setup()

    def runtest(self) -> None:
        runner_fixture_id = f"_{self._loop_scope}_scoped_runner"
        runner = self._request.getfixturevalue(runner_fixture_id)
        context = contextvars.copy_context()
        synchronized_obj = _synchronize_coroutine(
            getattr(*self._synchronization_target_attr), runner, context
        )
        with MonkeyPatch.context() as c:
            c.setattr(*self._synchronization_target_attr, synchronized_obj)
            super().runtest()

    @functools.cached_property
    def _loop_scope(self) -> _ScopeName:
        """
        Return the scope of the asyncio event loop this item is run in.

        The effective scope is determined lazily. It is identical to to the
        `loop_scope` value of the closest `asyncio` pytest marker. If no such
        marker is present, the the loop scope is determined by the configuration
        value of `asyncio_default_test_loop_scope`, instead.
        """
        marker = self.get_closest_marker("asyncio")
        assert marker is not None
        default_loop_scope = _get_default_test_loop_scope(self.config)
        loop_scope = marker.kwargs.get("loop_scope") or marker.kwargs.get("scope")
        if loop_scope is None:
            return default_loop_scope
        else:
            return loop_scope

    @property
    def _synchronization_target_attr(self) -> tuple[object, str]:
        """
        Return the coroutine that needs to be synchronized during the test run.

        This method is intended to be overwritten by subclasses when they need to apply
        the coroutine synchronizer to a value that's different from self.obj
        e.g. the AsyncHypothesisTest subclass.
        """
        return self, "obj"


class Coroutine(PytestAsyncioFunction):
    """Pytest item created by a coroutine"""

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        func = item.obj
        return inspect.iscoroutinefunction(func)


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


class AsyncHypothesisTest(PytestAsyncioFunction):
    """
    Pytest item that is coroutine or an asynchronous generator decorated by
    @hypothesis.given.
    """

    def setup(self) -> None:
        if not getattr(self.obj, "hypothesis", False) and getattr(
            self.obj, "is_hypothesis_test", False
        ):
            pytest.fail(
                f"test function `{self!r}` is using Hypothesis, but pytest-asyncio "
                "only works with Hypothesis 3.64.0 or later."
            )
        return super().setup()

    @staticmethod
    def _can_substitute(item: Function) -> bool:
        func = item.obj
        return (
            getattr(func, "is_hypothesis_test", False)  # type: ignore[return-value]
            and getattr(func, "hypothesis", None)
            and inspect.iscoroutinefunction(func.hypothesis.inner_test)
        )

    @property
    def _synchronization_target_attr(self) -> tuple[object, str]:
        return self.obj.hypothesis, "inner_test"


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
            if (
                specialized_item_class is not None
                and _resolve_asyncio_marker(node) is not None
            ):
                updated_item = specialized_item_class._from_function(node)
        updated_node_collection.append(updated_item)
    hook_result.force_result(updated_node_collection)


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    specialized_item_class = PytestAsyncioFunction.item_subclass_for(
        metafunc.definition
    )
    if specialized_item_class is None:
        return

    asyncio_marker = _resolve_asyncio_marker(metafunc.definition)
    if asyncio_marker is None:
        return
    marker_loop_scope, marker_selected_factory_names = _parse_asyncio_marker(
        asyncio_marker
    )

    hook_factories = _collect_hook_loop_factories(metafunc.config, metafunc.definition)
    if hook_factories is None:
        if marker_selected_factory_names is not None:
            raise pytest.UsageError(
                "mark.asyncio 'loop_factories' requires at least one "
                "pytest_asyncio_loop_factories hook implementation."
            )
        return

    factory_params: Collection[object]
    factory_ids: Collection[str]
    if marker_selected_factory_names is None:
        factory_params = hook_factories.values()
        factory_ids = hook_factories.keys()
    else:
        # Iterate in marker order to preserve explicit user selection
        # order.
        factory_ids = marker_selected_factory_names
        factory_params = [
            (
                hook_factories[name]
                if name in hook_factories
                else pytest.param(
                    None,
                    marks=pytest.mark.skip(
                        reason=(
                            f"Loop factory {name!r} is not available."
                            f" Available factories:"
                            f" {', '.join(hook_factories)}."
                        ),
                    ),
                )
            )
            for name in marker_selected_factory_names
        ]
    metafunc.fixturenames.append(_asyncio_loop_factory.__name__)
    default_loop_scope = _get_default_test_loop_scope(metafunc.config)
    loop_scope = marker_loop_scope or default_loop_scope
    # pytest.HIDDEN_PARAM was added in pytest 8.4
    hide_id = len(factory_ids) == 1 and hasattr(pytest, "HIDDEN_PARAM")
    metafunc.parametrize(
        _asyncio_loop_factory.__name__,
        factory_params,
        ids=(pytest.HIDDEN_PARAM,) if hide_id else factory_ids,
        indirect=True,
        scope=loop_scope,
    )


def _synchronize_coroutine(
    func: Callable[..., CoroutineType],
    runner,
    context: contextvars.Context,
):
    """
    Return a sync wrapper around a coroutine executing it in the
    specified runner and context.
    """

    @functools.wraps(func)
    def inner(*args, **kwargs):
        coro = func(*args, **kwargs)
        runner.run(coro, context=context)

    return inner


def is_async_test(item: Item) -> TypeIs[PytestAsyncioFunction]:
    """Returns whether a test item is a pytest-asyncio test"""
    return isinstance(item, PytestAsyncioFunction)
