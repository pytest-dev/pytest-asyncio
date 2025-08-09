import asyncio

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [1, 2, 3])
async def test_parametrized_async_function(value):
    await asyncio.sleep(1)
    assert value > 0
