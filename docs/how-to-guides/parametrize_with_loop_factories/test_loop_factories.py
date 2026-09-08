import asyncio

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [1, 2])
async def test_selected_loop(value):
    loop_name = type(asyncio.get_running_loop()).__name__
    assert loop_name in {"FirstLoop", "SecondLoop"}
    assert await asyncio.sleep(0, result=value) == value
