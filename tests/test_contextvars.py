"""Quick'n'dirty unit tests for provided fixtures and markers."""
import asyncio
import pytest

import pytest_asyncio.plugin

from contextvars import ContextVar


ctxvar = ContextVar('ctxvar')


@pytest.fixture
async def set_some_context(context):
    ctxvar.set('quarantine is fun')


@pytest.mark.asyncio
async def test_test(set_some_context):
    # print ("Context in test:", list(context.items()))
    assert ctxvar.get() == 'quarantine is fun'
