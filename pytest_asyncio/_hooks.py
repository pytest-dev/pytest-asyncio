"""Hook specifications and shared type aliases for pytest-asyncio."""

from __future__ import annotations

from asyncio import AbstractEventLoop
from collections.abc import Callable, Mapping
from typing import Literal, TypeAlias

import pluggy
from pytest import Config, Item

_ScopeName = Literal["session", "package", "module", "class", "function"]
LoopFactory: TypeAlias = Callable[[], AbstractEventLoop]


class PytestAsyncioError(Exception):
    """Base class for exceptions raised by pytest-asyncio"""


hookspec = pluggy.HookspecMarker("pytest")


class PytestAsyncioSpecs:
    @hookspec(firstresult=True)
    def pytest_asyncio_loop_factories(
        self,
        config: Config,
        item: Item,
    ) -> Mapping[str, LoopFactory] | None:
        raise NotImplementedError  # pragma: no cover
