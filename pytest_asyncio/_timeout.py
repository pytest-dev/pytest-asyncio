"""Cooperative delivery of pytest-timeout's signal failures."""

from __future__ import annotations

import asyncio
import contextvars
import sys
import threading
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

import pytest

__tracebackhide__ = True
_T = TypeVar("_T")


@dataclass
class _Delivery:
    config: pytest.Config
    loop: asyncio.AbstractEventLoop
    closing: bool = False
    exception: BaseException | None = None
    timeout: asyncio.Timeout | None = None

    def run(self, operation: Callable[[], _T]) -> _T:
        previous = self.config.stash.get(_CURRENT_DELIVERY, None)
        try:
            try:
                self.config.stash[_CURRENT_DELIVERY] = self
                result = operation()
            finally:
                # Once the runner returns, a new signal can fail synchronously.
                # Stop claiming it before deciding which outcome to propagate.
                self.config.stash[_CURRENT_DELIVERY] = previous
        except (KeyboardInterrupt, SystemExit, pytest.exit.Exception):
            raise
        except asyncio.CancelledError as exc:
            if self.exception is None:
                raise
            # asyncio.Timeout converts only its own cancellation to TimeoutError.
            # Preserve cancellation requested by another caller.
            raise exc from self.exception
        except BaseException as exc:
            if self.exception is None or exc is self.exception:
                raise
            raise self.exception from exc
        if self.exception is not None:
            raise self.exception
        return result

    def interrupt(self) -> None:
        if self.config.stash.get(_CURRENT_DELIVERY, None) is not self:
            return
        if self.closing:
            # A completed shutdown phase can consume stop(). Keep stopping
            # until Runner.close() returns; never stop a reusable invocation.
            self.loop.stop()
            self.loop.call_soon(self.interrupt)
        elif self.timeout is not None:
            self.timeout.reschedule(self.loop.time())


# SIGALRM only reaches the main thread; worker runners keep their native behavior.
_CURRENT_DELIVERY = pytest.StashKey[_Delivery | None]()


def _supports_cooperative_timeouts(config: pytest.Config) -> bool:
    # Test modules can load pytest-timeout after pytest_configure has run.
    return (
        sys.version_info >= (3, 11)
        and threading.current_thread() is threading.main_thread()
        and config.hook.pytest_timeout_expired.has_spec()
    )


@pytest.hookimpl(tryfirst=True, optionalhook=True)
def pytest_timeout_expired(item: pytest.Item, exception: BaseException) -> bool | None:
    if threading.current_thread() is not threading.main_thread():
        return None
    invocation = item.config.stash.get(_CURRENT_DELIVERY, None)
    if invocation is None:
        return None
    if invocation.exception is None:
        invocation.exception = exception
        # Raising here can interrupt asyncio before it schedules a task's next
        # step. Return to the interrupted code and cancel at a safe loop turn.
        # Late callbacks check ownership instead of relying on Handle.cancel():
        # SIGINT can interrupt scheduling before the handle is returned.
        if not invocation.loop.is_closed():
            invocation.loop.call_soon_threadsafe(invocation.interrupt)
    return True


def run(
    runner: asyncio.Runner,
    coro_factory: Callable[[], Coroutine[Any, Any, _T]],
    *,
    context: contextvars.Context,
    config: pytest.Config,
) -> _T:
    """Run a native coroutine factory with cooperative timeout delivery."""
    if not _supports_cooperative_timeouts(config):
        return runner.run(coro_factory(), context=context)

    invocation = _Delivery(config, runner.get_loop())

    async def invoke() -> _T:
        if invocation.exception is not None:
            raise invocation.exception
        try:
            async with asyncio.timeout(None) as timeout:
                invocation.timeout = timeout
                # Create the user coroutine only once its task owns execution.
                # Runner and task factories retain ownership of invoke().
                return await coro_factory()
        finally:
            # The signal may have queued delivery just as the coroutine exits.
            # Do not reschedule a timeout whose context has already exited.
            invocation.timeout = None

    return invocation.run(lambda: runner.run(invoke(), context=context))


def close(runner: asyncio.Runner, *, config: pytest.Config) -> None:
    if not _supports_cooperative_timeouts(config):
        runner.close()
        return
    _Delivery(config, runner.get_loop(), closing=True).run(runner.close)
