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
async def var_fixture_1(no_var_fixture):
    with context_var_manager("value1"):
        yield


@pytest.fixture(scope="function")
async def var_nop_fixture(var_fixture_1):
    with context_var_manager(_context_var.get()):
        yield


@pytest.fixture(scope="function")
def var_fixture_2(var_nop_fixture):
    assert _context_var.get() == "value1"
    with context_var_manager("value2"):
        yield


@pytest.fixture(scope="function")
async def var_fixture_3(var_fixture_2):
    assert _context_var.get() == "value2"
    with context_var_manager("value3"):
        yield


@pytest.mark.asyncio
@pytest.mark.xfail(
    sys.version_info < (3, 11), reason="requires asyncio Task context support"
)
async def test(var_fixture_3):
    assert _context_var.get() == "value3"
