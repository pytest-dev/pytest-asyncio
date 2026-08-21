"""Cooperative delivery of pytest-timeout's signal failures."""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import sys
import threading
from collections.abc import Coroutine, Iterator
from dataclasses import dataclass
from typing import Any, TypeVar

import pytest

if sys.version_info >= (3, 11):
    from asyncio import Runner
else:
    from backports.asyncio.runner import Runner


class _RunnerState(threading.local):
    invocation: _Delivery | None = None


@dataclass
class _Delivery:
    loop: asyncio.AbstractEventLoop
    exception: BaseException | None = None
    handle: asyncio.Handle | None = None
    timeout_cancellation: bool = False

    def interrupt(self, state: _RunnerState) -> None:
        raise NotImplementedError


@dataclass
class _Invocation(_Delivery):
    task: asyncio.Task[Any] | None = None
    cancellation_requested: bool = False

    def interrupt(self, state: _RunnerState) -> None:
        self.handle = None
        if state.invocation is self and self.task is not None:
            self.cancellation_requested = self.task.cancel()


@dataclass
class _Shutdown(_Delivery):
    def interrupt(self, state: _RunnerState) -> None:
        self.handle = None
        if state.invocation is self:
            # Runner.close() owns the loop and closes it in a finally block.
            # Stop only that final shutdown, never a reusable runner invocation.
            self.loop.stop()


_RUNNER_STATE = pytest.StashKey[_RunnerState]()
_T = TypeVar("_T")


def configure(config: pytest.Config) -> None:
    enabled = config.getoption("asyncio_cooperative_timeouts") or config.getini(
        "asyncio_cooperative_timeouts"
    )
    if not enabled:
        return
    if not config.hook.pytest_timeout_expired.has_spec():
        raise pytest.UsageError(
            "asyncio_cooperative_timeouts requires pytest-timeout's "
            "pytest_timeout_expired hook"
        )
    config.stash[_RUNNER_STATE] = _RunnerState()


@pytest.hookimpl(tryfirst=True, optionalhook=True)
def pytest_timeout_expired(item: pytest.Item, exception: BaseException) -> bool | None:
    state = item.config.stash.get(_RUNNER_STATE, None)
    if state is None or state.invocation is None:
        return None
    invocation = state.invocation
    if invocation.exception is None:
        invocation.exception = exception
        # Raising here can interrupt asyncio before it schedules a task's next
        # step. Return to the interrupted code and cancel at a safe loop turn.
        if not invocation.loop.is_closed():
            invocation.handle = invocation.loop.call_soon_threadsafe(
                invocation.interrupt, state
            )
    return True


@contextlib.contextmanager
def _deliver(config: pytest.Config, invocation: _Delivery) -> Iterator[None]:
    state = config.stash[_RUNNER_STATE]
    previous = state.invocation
    state.invocation = invocation
    try:
        try:
            yield
        finally:
            # Once the runner returns, a new signal can fail synchronously.
            # Stop claiming it before deciding which outcome to propagate.
            state.invocation = previous
            if invocation.handle is not None:
                invocation.handle.cancel()
    except (KeyboardInterrupt, SystemExit, pytest.exit.Exception):
        raise
    except asyncio.CancelledError as exc:
        if invocation.exception is None:
            raise
        if invocation.timeout_cancellation:
            raise invocation.exception from exc
        # Preserve cancellation when another caller requested it, or when a
        # custom Task cannot tell us whose cancellation is being delivered.
        raise exc from invocation.exception
    except BaseException as exc:
        if invocation.exception is None or exc is invocation.exception:
            raise
        raise invocation.exception from exc
    if invocation.exception is not None:
        raise invocation.exception


def run(
    runner: Runner,
    coro: Coroutine[Any, Any, _T],
    *,
    context: contextvars.Context,
    config: pytest.Config,
) -> _T:
    if _RUNNER_STATE not in config.stash:
        return runner.run(coro, context=context)

    invocation = _Invocation(runner.get_loop())

    async def invoke() -> _T:
        task = asyncio.current_task()
        assert task is not None
        invocation.task = task
        if invocation.exception is not None:
            coro.close()
            raise invocation.exception
        # A custom Python 3.10 task factory can bypass the runner backport's
        # Task, which provides the cancellation-count methods added in 3.11.
        get_cancelling = getattr(task, "cancelling", None)
        uncancel = getattr(task, "uncancel", None)
        cancelling = get_cancelling() if get_cancelling is not None else 0
        try:
            return await coro
        finally:
            if invocation.cancellation_requested and uncancel is not None:
                # Remove only our cancellation before Runner handles SIGINT.
                # A concurrent external cancellation must still propagate.
                remaining = uncancel()
                invocation.timeout_cancellation = (
                    get_cancelling is not None and remaining <= cancelling
                )

    wrapped = invoke()
    try:
        with _deliver(config, invocation):
            return runner.run(wrapped, context=context)
    finally:
        if invocation.task is None:
            wrapped.close()
            coro.close()


def close(runner: Runner, *, config: pytest.Config) -> None:
    if _RUNNER_STATE not in config.stash:
        runner.close()
        return
    with _deliver(config, _Shutdown(runner.get_loop())):
        runner.close()
