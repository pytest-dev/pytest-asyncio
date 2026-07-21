"""pytest-asyncio implementation."""

from __future__ import annotations

import contextlib
import socket
from collections.abc import Callable

import pytest

from ._collection import (
    is_async_test,
    pytest_generate_tests,
    pytest_pycollect_makeitem_tag_async_items,
    pytest_runtest_setup,
)
from ._config import pytest_addoption, pytest_configure, pytest_report_header
from ._dispatch import pytest_pyfunc_call
from ._fixtures import fixture, pytest_fixture_setup
from ._hooks import PytestAsyncioError
from ._runner import (
    _asyncio_loop_factory,
    _class_scoped_runner,
    _function_scoped_runner,
    _module_scoped_runner,
    _package_scoped_runner,
    _session_scoped_runner,
)
from ._usage_checks import pytest_collection_finish

__all__ = [
    "PytestAsyncioError",
    "_asyncio_loop_factory",
    "_class_scoped_runner",
    "_function_scoped_runner",
    "_module_scoped_runner",
    "_package_scoped_runner",
    "_session_scoped_runner",
    "fixture",
    "is_async_test",
    "pytest_addoption",
    "pytest_collection_finish",
    "pytest_configure",
    "pytest_fixture_setup",
    "pytest_generate_tests",
    "pytest_pycollect_makeitem_tag_async_items",
    "pytest_pyfunc_call",
    "pytest_report_header",
    "pytest_runtest_setup",
    "unused_tcp_port",
    "unused_tcp_port_factory",
    "unused_udp_port",
    "unused_udp_port_factory",
]


def _unused_port(socket_type: int) -> int:
    """Find an unused localhost port from 1024-65535 and return it."""
    with contextlib.closing(socket.socket(type=socket_type)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def unused_tcp_port() -> int:
    return _unused_port(socket.SOCK_STREAM)


@pytest.fixture
def unused_udp_port() -> int:
    return _unused_port(socket.SOCK_DGRAM)


@pytest.fixture(scope="session")
def unused_tcp_port_factory() -> Callable[[], int]:
    """A factory function, producing different unused TCP ports."""
    produced = set()

    def factory():
        """Return an unused port."""
        port = _unused_port(socket.SOCK_STREAM)

        while port in produced:
            port = _unused_port(socket.SOCK_STREAM)

        produced.add(port)

        return port

    return factory


@pytest.fixture(scope="session")
def unused_udp_port_factory() -> Callable[[], int]:
    """A factory function, producing different unused UDP ports."""
    produced = set()

    def factory():
        """Return an unused port."""
        port = _unused_port(socket.SOCK_DGRAM)

        while port in produced:
            port = _unused_port(socket.SOCK_DGRAM)

        produced.add(port)

        return port

    return factory
