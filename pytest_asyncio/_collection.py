"""Collection of asyncio tests: tag collected async functions as pytest-asyncio's."""

from __future__ import annotations

import inspect
from collections.abc import Collection, Generator, Sequence

import pluggy
import pytest
from pytest import Function, Item, PytestCollectionWarning

from ._config import _get_default_test_loop_scope
from ._hooks import _ScopeName
from ._markers import (
    _collect_hook_loop_factories,
    _parse_asyncio_marker,
    _resolve_asyncio_marker,
)
from ._runner import _asyncio_loop_factory

asyncio_test_key: pytest.StashKey[bool] = pytest.StashKey()
loop_scope_key: pytest.StashKey[_ScopeName] = pytest.StashKey()
_hypothesis_version_incompatible_key: pytest.StashKey[bool] = pytest.StashKey()


def _is_coroutine_or_asyncgen(obj: object) -> bool:
    return inspect.iscoroutinefunction(obj) or inspect.isasyncgenfunction(obj)


def _is_hypothesis_wrapped_coroutine(func: object) -> bool:
    return bool(
        getattr(func, "is_hypothesis_test", False)
        and getattr(func, "hypothesis", None)
        and inspect.iscoroutinefunction(func.hypothesis.inner_test)
    )


def _classify_async_function(func: object) -> str | None:
    """
    Classify a collected test function, mirroring the precedence of
    pytest-asyncio's historical Item-subclass hierarchy exactly (first
    matching category wins, in this order). In particular, a
    staticmethod-wrapped async generator is classified "staticmethod", not
    "asyncgen" -- the unsupported-async-generator rejection below only ever
    applied to plain (non-staticmethod) async generators, and that quirk is
    preserved here rather than "fixed".

    Returns None if `func` isn't async-shaped at all, in which case
    pytest-asyncio does not take ownership of it.
    """
    if inspect.iscoroutinefunction(func):
        return "coroutine"
    if inspect.isasyncgenfunction(func):
        return "asyncgen"
    if isinstance(func, staticmethod) and _is_coroutine_or_asyncgen(func.__func__):
        return "staticmethod"
    if _is_hypothesis_wrapped_coroutine(func):
        return "hypothesis"
    return None


def _synchronization_target(item: Function) -> tuple[object, str]:
    """
    Return the (obj, attr) pair that needs to be monkeypatched with a
    synchronized wrapper while the test runs. Normally this is the item
    itself, but a Hypothesis-wrapped (`@given`) coroutine lives at
    `item.obj.hypothesis.inner_test`, not `item.obj`.
    """
    if _classify_async_function(item.obj) == "hypothesis":
        return item.obj.hypothesis, "inner_test"
    return item, "obj"


def _compute_test_loop_scope(item: Function) -> _ScopeName:
    marker = item.get_closest_marker("asyncio")
    assert marker is not None
    loop_scope = marker.kwargs.get("loop_scope")
    if loop_scope is not None:
        return loop_scope
    return _get_default_test_loop_scope(item.config)


# The function name needs to start with "pytest_"
# see https://github.com/pytest-dev/pytest/issues/11307
@pytest.hookimpl(specname="pytest_pycollect_makeitem", hookwrapper=True)
def pytest_pycollect_makeitem_tag_async_items(
    collector: pytest.Module | pytest.Class, name: str, obj: object
) -> Generator[None, pluggy.Result, None]:
    """
    Tags coroutines, async generators, and their staticmethod/Hypothesis-wrapped
    variants -- collected as plain pytest.Function items -- as pytest-asyncio
    tests, and computes/stashes the loop scope each one runs under.
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
    for node in node_iterator:
        if not isinstance(node, Function):
            continue
        category = _classify_async_function(node.obj)
        if category is None:
            continue
        if _resolve_asyncio_marker(node) is None:
            continue
        node.stash[asyncio_test_key] = True
        if category == "asyncgen":
            unsupported_item_type_message = (
                f"Tests based on asynchronous generators are not supported. "
                f"{node.name} will be ignored."
            )
            node.warn(PytestCollectionWarning(unsupported_item_type_message))
            node.add_marker(
                pytest.mark.xfail(run=False, reason=unsupported_item_type_message)
            )
        if (
            category == "hypothesis"
            and not getattr(node.obj, "hypothesis", False)
            and getattr(node.obj, "is_hypothesis_test", False)
        ):
            node.stash[_hypothesis_version_incompatible_key] = True
        loop_scope = _compute_test_loop_scope(node)
        node.stash[loop_scope_key] = loop_scope
        # Insert (rather than append) so that _fillfixtures(), which resolves
        # item.fixturenames strictly in order, resolves the loop factory
        # before any other same-scope async fixture. A loop-factory variant
        # change must tear down the stale runner (and, via the finalizer
        # chaining in pytest_fixture_setup, any other async fixture cached
        # under it) before those fixtures are resolved for this item -- and
        # that can only happen if something actually requests the (side
        # effect free) loop factory value early. The runner fixture id itself
        # is *appended*, deliberately staying last: unlike the loop factory,
        # creating/entering the runner has real side effects (it becomes the
        # current asyncio event loop), so it must not be resolved ahead of
        # ordinary same-scope fixtures that assume no loop is current yet.
        if _asyncio_loop_factory.__name__ not in node.fixturenames:
            node.fixturenames.insert(0, _asyncio_loop_factory.__name__)
        runner_fixture_id = f"_{loop_scope}_scoped_runner"
        if runner_fixture_id not in node.fixturenames:
            node.fixturenames.append(runner_fixture_id)


@pytest.hookimpl(tryfirst=True)
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if _classify_async_function(metafunc.definition.obj) is None:
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


@pytest.hookimpl
def pytest_runtest_setup(item: Item) -> None:
    if not is_async_test(item):
        return
    if item.stash.get(_hypothesis_version_incompatible_key, False):
        pytest.fail(
            f"test function `{item!r}` is using Hypothesis, but pytest-asyncio "
            "only works with Hypothesis 3.64.0 or later."
        )


def is_async_test(item: Item) -> bool:
    """Returns whether a test item is a pytest-asyncio test"""
    return item.stash.get(asyncio_test_key, False)
