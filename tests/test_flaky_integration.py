"""Tests for the Flaky integration, which retries failed tests.
"""
import asyncio

import flaky
import pytest

_threshold = -1


@flaky.flaky(3, 2)
@pytest.mark.asyncio
async def test_asyncio_flaky_thing_that_fails_then_succeeds():
    global _threshold
    await asyncio.sleep(0.1)
    _threshold += 1
    assert _threshold != 1
