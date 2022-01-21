import asyncio
from typing import Awaitable, TypeVar, Union

import pytest

_R = TypeVar("_R")


class Runner:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._task = None
        self._timeout_hande = None
        self._timeout_reached = False

    def run(self, coro: Awaitable[_R]) -> _R:
        return self._loop.run_until_complete(self._async_wrapper(coro))

    def run_test(self, coro: Awaitable[None]) -> None:
        task = asyncio.ensure_future(coro, loop=self._loop)
        try:
            self.run(task)
        except BaseException:
            # run_until_complete doesn't get the result from exceptions
            # that are not subclasses of `Exception`. Consume all
            # exceptions to prevent asyncio's warning from logging.
            if task.done() and not task.cancelled():
                task.exception()
            raise

    def set_timer(self, timeout: Union[int, float]) -> None:
        if self._timeout_hande is not None:
            self._timeout_hande.cancel()
        self._timeout_reached = False
        self._timeout_hande = self._loop.call_later(timeout, self._on_timeout)

    def cancel_timer(self) -> None:
        if self._timeout_hande is not None:
            self._timeout_hande.cancel()
        self._timeout_reached = False
        self._timeout_hande = None

    async def _async_wrapper(self, coro: Awaitable[_R]) -> _R:
        if self._timeout_reached:
            # timeout can happen in a gap between tasks execution,
            # it should be handled anyway
            raise asyncio.TimeoutError()
        task = asyncio.current_task()
        assert self._task is None
        self._task = task
        try:
            return await coro
        except asyncio.CancelledError:
            if self._timeout_reached:
                raise asyncio.TimeoutError()
        finally:
            self._task = None

    def _on_timeout(self) -> None:
        # the plugin is optional,
        # pytest-asyncio should work fine without pytest-timeout
        # That's why the lazy import is required here
        import pytest_timeout

        if pytest_timeout.is_debugging():
            return
        self._timeout_reached = True
        if self._task is not None:
            self._task.cancel()


def _install_runner(item: pytest.Item, loop: asyncio.AbstractEventLoop) -> None:
    item._pytest_asyncio_runner = Runner(loop)


def _get_runner(item: pytest.Item) -> Runner:
    runner = getattr(item, "_pytest_asyncio_runner", None)
    if runner is not None:
        return runner
    else:
        parent = item.parent
        if parent is not None:
            parent_runner = _get_runner(parent)
            runner = item._pytest_asyncio_runner = Runner(parent_runner._loop)
            return runner
        else:  # pragma: no cover
            # can happen only if the plugin is broken and no event_loop fixture
            # dependency was installed.
            raise RuntimeError(f"There is no event_loop associated with {item}")
