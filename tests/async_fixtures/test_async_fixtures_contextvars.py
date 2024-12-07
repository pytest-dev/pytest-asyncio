"""
Regression test for https://github.com/pytest-dev/pytest-asyncio/issues/127:
contextvars were not properly maintained among fixtures and tests.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar

import pytest

_context_var = ContextVar("context_var")


@contextmanager
def context_var_manager(value):
    token = _context_var.set(value)
    try:
        yield
    finally:
        _context_var.reset(token)


@pytest.fixture(scope="function")
async def no_var_fixture():
    with pytest.raises(LookupError):
        _context_var.get()
    yield
    with pytest.raises(LookupError):
        _context_var.get()


@pytest.fixture(scope="function")
async def var_fixture(no_var_fixture):
    with context_var_manager("value"):
        yield


@pytest.fixture(scope="function")
async def var_nop_fixture(var_fixture):
    with context_var_manager(_context_var.get()):
        yield


@pytest.fixture(scope="function")
def inner_var_fixture(var_nop_fixture):
    assert _context_var.get() == "value"
    with context_var_manager("value2"):
        yield


@pytest.mark.asyncio
@pytest.mark.xfail(
    sys.version_info < (3, 11), reason="requires asyncio Task context support"
)
async def test(inner_var_fixture):
    assert _context_var.get() == "value2"
