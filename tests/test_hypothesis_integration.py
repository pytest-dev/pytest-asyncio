"""Tests for the Hypothesis integration, which wraps async functions in a
sync shim for Hypothesis.
"""
import asyncio

import pytest

from hypothesis import given, strategies as st


@given(st.integers())
@pytest.mark.asyncio
async def test_mark_inner(n):
    assert isinstance(n, int)


@pytest.mark.asyncio
@given(st.integers())
async def test_mark_outer(n):
    assert isinstance(n, int)


@pytest.mark.parametrize("y", [1, 2])
@given(x=st.none())
@pytest.mark.asyncio
async def test_mark_and_parametrize(x, y):
    assert x is None
    assert y in (1, 2)


@given(st.integers())
@pytest.mark.asyncio
async def test_can_use_fixture_provided_event_loop(event_loop, n):
    semaphore = asyncio.Semaphore(value=0, loop=event_loop)
    event_loop.call_soon(semaphore.release)
    await semaphore.acquire()
