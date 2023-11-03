import asyncio

import pytest


class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    pass


@pytest.fixture(scope="module")
def event_loop_policy(request):
    return CustomEventLoopPolicy()


@pytest.mark.asyncio(scope="module")
async def test_uses_custom_event_loop_policy():
    assert isinstance(asyncio.get_event_loop_policy(), CustomEventLoopPolicy)
