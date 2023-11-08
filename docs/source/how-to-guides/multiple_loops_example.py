import asyncio
from asyncio import DefaultEventLoopPolicy

import pytest


class CustomEventLoopPolicy(DefaultEventLoopPolicy):
    pass


@pytest.fixture(
    scope="session",
    params=(
        CustomEventLoopPolicy(),
        CustomEventLoopPolicy(),
    ),
)
def event_loop_policy(request):
    return request.param


@pytest.mark.asyncio
async def test_uses_custom_event_loop_policy():
    assert isinstance(asyncio.get_event_loop_policy(), CustomEventLoopPolicy)
