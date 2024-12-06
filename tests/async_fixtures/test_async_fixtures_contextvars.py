"""
Regression test for https://github.com/pytest-dev/pytest-asyncio/issues/127:
contextvars were not properly maintained among fixtures and tests.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from contextvars import ContextVar

import pytest


@asynccontextmanager
async def context_var_manager():
    context_var = ContextVar("context_var")
    token = context_var.set("value")
    try:
        yield context_var
    finally:
        context_var.reset(token)


@pytest.fixture(scope="function")
async def context_var():
    async with context_var_manager() as v:
        yield v


@pytest.mark.asyncio
@pytest.mark.xfail(
    sys.version_info < (3, 11), reason="requires asyncio Task context support"
)
async def test(context_var):
    assert context_var.get() == "value"
