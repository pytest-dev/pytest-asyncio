import asyncio

import pytest

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_example():
    """No marker!"""
    await asyncio.sleep(0)
