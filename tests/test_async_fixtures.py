"""Tests for async fixtures."""
import asyncio

import pytest
from pytest_asyncio import async_fixture

@pytest.fixture
def shared_state():
    """Some shared state, so we can assert the order of operations."""
    return {}


@async_fixture
def minimal_async_fixture(shared_state):
    """A minimal asyncio fixture."""
    shared_state['async_fixture'] = 1
    yield from asyncio.sleep(0.01)
    shared_state['async_fixture'] += 1


@pytest.mark.asyncio
def test_minimal_asynx_fixture(shared_state, minimal_async_fixture):
    """Test minimal async fixture working."""
    assert shared_state['async_fixture'] == 2
    yield from asyncio.sleep(0)
