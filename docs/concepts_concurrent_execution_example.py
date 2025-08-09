import asyncio

import pytest


@pytest.mark.asyncio
async def test_first():
    await asyncio.sleep(2)  # Takes 2 seconds


@pytest.mark.asyncio
async def test_second():
    await asyncio.sleep(2)  # Takes 2 seconds


# Total execution time: ~4 seconds, not ~2 seconds
