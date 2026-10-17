"""Dispatch of asyncio tests: synchronized execution plus pre-flight warnings."""

from __future__ import annotations

import contextvars
import functools
import warnings
from collections.abc import Callable
from types import CoroutineType

import pytest
from pytest import Function, MonkeyPatch, PytestDeprecationWarning

from ._collection import (
    _is_coroutine_or_asyncgen,
    _synchronization_target,
    is_async_test,
    loop_scope_key,
    loop_scope_mismatches_key,
)
from ._config import Mode, _get_asyncio_mode
from ._fixtures import _is_asyncio_fixture_function
from ._mismatch import PytestAsyncioLoopScopeMismatchWarning


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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem: Function) -> object | None:
    """Pytest hook called before a test case is run."""
    if pyfuncitem.get_closest_marker("asyncio") is not None:
        if is_async_test(pyfuncitem):
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
                            "pytest-asyncio."
                        ),
                        stacklevel=1,
                    )
                    # no stacklevel points at the users code, so we set stacklevel=1
                    # so it at least indicates that it's the plugin complaining.
                    # Pytest gives the test file & name in the warnings summary at least

            loop_scope = pyfuncitem.stash[loop_scope_key]
            for fixture_name, fixture_loop_scope in pyfuncitem.stash.get(
                loop_scope_mismatches_key, ()
            ):
                warnings.warn(
                    PytestAsyncioLoopScopeMismatchWarning(
                        f"{pyfuncitem.nodeid}: the test's effective loop_scope "
                        f"{loop_scope!r} differs from fixture {fixture_name!r}'s "
                        f"effective loop_scope {fixture_loop_scope!r}. The fixture "
                        "will run on a different event loop than the test, which "
                        "can silently break objects (e.g. asyncio.Future, Task, or "
                        "Lock) bound to the loop they were created on."
                    ),
                    stacklevel=1,
                )
            runner_fixture_id = f"_{loop_scope}_scoped_runner"
            runner = pyfuncitem._request.getfixturevalue(runner_fixture_id)  # type: ignore[attr-defined]
            context = contextvars.copy_context()
            target_obj, target_attr = _synchronization_target(pyfuncitem)
            synchronized_obj = _synchronize_coroutine(
                getattr(target_obj, target_attr), runner, context
            )
            with MonkeyPatch.context() as c:
                c.setattr(target_obj, target_attr, synchronized_obj)
                yield
            return None
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
