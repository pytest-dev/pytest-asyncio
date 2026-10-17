"""Event loop / asyncio.Runner lifecycle management, scoped by pytest fixture scope."""

from __future__ import annotations

import asyncio
import contextlib
import sys
import traceback
import warnings
from asyncio import AbstractEventLoop
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

import pytest
from pytest import FixtureRequest

from ._config import _get_asyncio_debug
from ._hooks import LoopFactory, _ScopeName

if sys.version_info >= (3, 11):
    from asyncio import Runner
else:
    from backports.asyncio.runner import Runner

if TYPE_CHECKING:
    # AbstractEventLoopPolicy is deprecated and scheduled for removal in Python 3.16
    # Import it for type checking only to avoid raising a DeprecationWarning.
    from asyncio import AbstractEventLoopPolicy


@contextlib.contextmanager
def _temporary_event_loop(loop: AbstractEventLoop) -> Iterator[None]:
    try:
        old_loop = _get_event_loop_no_warn()
    except RuntimeError:
        old_loop = None
    if old_loop is loop:
        yield
        return
    _set_event_loop(loop)
    try:
        yield
    finally:
        _set_event_loop(old_loop)


@contextlib.contextmanager
def _temporary_event_loop_policy(
    policy: AbstractEventLoopPolicy,
) -> Iterator[None]:
    old_loop_policy = _get_event_loop_policy()
    _set_event_loop_policy(policy)
    try:
        yield
    finally:
        _set_event_loop_policy(old_loop_policy)


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


_RUNNER_TEARDOWN_WARNING = """\
An exception occurred during teardown of an asyncio.Runner. \
The reason is likely that you closed the underlying event loop in a test, \
which prevents the cleanup of asynchronous generators by the runner.
This warning will become an error in future versions of pytest-asyncio. \
Please ensure that your tests don't close the event loop. \
Here is the traceback of the exception triggered during teardown:
%s
"""


def _create_scoped_runner_fixture(scope: _ScopeName) -> Callable:
    @pytest.fixture(
        scope=scope,
        name=f"_{scope}_scoped_runner",
    )
    def _scoped_runner(
        _asyncio_loop_factory,
        request: FixtureRequest,
    ) -> Iterator[Runner]:
        new_loop_policy = _get_event_loop_policy()
        debug_mode = _get_asyncio_debug(request.config)
        with _temporary_event_loop_policy(new_loop_policy):
            runner = Runner(
                debug=debug_mode,
                loop_factory=_asyncio_loop_factory,
            ).__enter__()
            if _asyncio_loop_factory is not None:
                _set_event_loop(runner.get_loop())
            try:
                yield runner
            except Exception as e:
                runner.__exit__(type(e), e, e.__traceback__)
            else:
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore", ".*BaseEventLoop.shutdown_asyncgens.*", RuntimeWarning
                    )
                    try:
                        runner.__exit__(None, None, None)
                    except RuntimeError:
                        warnings.warn(
                            _RUNNER_TEARDOWN_WARNING % traceback.format_exc(),
                            RuntimeWarning,
                        )
            finally:
                if _asyncio_loop_factory is not None:
                    _set_event_loop(None)

    return _scoped_runner


_function_scoped_runner = _create_scoped_runner_fixture("function")
_class_scoped_runner = _create_scoped_runner_fixture("class")
_module_scoped_runner = _create_scoped_runner_fixture("module")
_package_scoped_runner = _create_scoped_runner_fixture("package")
_session_scoped_runner = _create_scoped_runner_fixture("session")


@pytest.fixture(scope="session")
def _asyncio_loop_factory(request: FixtureRequest) -> LoopFactory | None:
    return getattr(request, "param", None)
