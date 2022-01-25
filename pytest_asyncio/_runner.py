import asyncio
import contextlib
from typing import Awaitable, List, Optional, TypeVar

import aioloop_proxy
import pytest

_R = TypeVar("_R")


class Runner:
    __slots__ = ("_loop", "_node", "_children", "_loop_proxy_cm")

    def __init__(self, node: pytest.Item, loop: asyncio.AbstractEventLoop) -> None:
        self._node = node
        # children nodes that uses asyncio
        # the list can be reset if the current node re-assigns the loop
        self._children: List[Runner] = []
        self._loop_proxy_cm: Optional[
            "contextlib.AbstractContextManager[asyncio.AbstractEventLoop]"
        ] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._set_loop(loop)

    @classmethod
    def install(
        cls, request: pytest.FixtureRequest, loop: asyncio.AbstractEventLoop
    ) -> None:
        node = request.node
        runner = getattr(node, "_asyncio_runner", None)
        if runner is None:
            runner = cls(node, loop)
            node._asyncio_runner = runner
        else:
            # parametrized non-function scope loop was recalculated
            # with other params of precessors
            runner._set_loop(loop)
        request.addfinalizer(runner._uninstall)

    @classmethod
    def uninstall(cls, request: pytest.FixtureRequest) -> None:
        node = request.node
        runner = getattr(node, "_asyncio_runner", None)
        assert runner is not None
        runner._uninstall()

    @classmethod
    def get(cls, node: pytest.Item) -> "Runner":
        runner = getattr(node, "_asyncio_runner", None)
        if runner is not None:
            return runner
        parent_node = node.parent
        if parent_node is None:
            # should never happen if pytest_fixture_setup works correctly
            raise RuntimeError("Cannot find a node with installed loop")
        parent_runner = cls.get(parent_node)
        runner = cls(node, parent_runner._loop)
        node._asyncio_runner = runner
        node.addfinalizer(runner._uninstall)
        return runner

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

    def run(self, coro: Awaitable[_R]) -> _R:
        return self._loop.run_until_complete(coro)

    def _set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        assert loop is not None
        if self._loop_proxy_cm is not None:
            self._loop_proxy_cm.__exit__(None, None, None)
        self._loop_proxy_cm = aioloop_proxy.proxy(loop)
        self._loop = self._loop_proxy_cm.__enter__()
        # cleanup children runners, recreate them on the next run
        for child in self._children:
            child._uninstall()
        self._children.clear()

    def _uninstall(self) -> None:
        if self._loop_proxy_cm is not None:
            self._loop_proxy_cm.__exit__(None, None, None)
        self._loop_proxy_cm = None
        self._loop = None
        delattr(self._node, "_asyncio_runner")
