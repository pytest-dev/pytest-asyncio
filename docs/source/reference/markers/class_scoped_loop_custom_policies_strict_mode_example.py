import asyncio

import pytest


@pytest.fixture(
    params=[
        asyncio.DefaultEventLoopPolicy(),
        asyncio.DefaultEventLoopPolicy(),
    ]
)
def event_loop_policy(request):
    return request.param


class TestWithDifferentLoopPolicies:
    @pytest.mark.asyncio
    async def test_parametrized_loop(self):
        pass
