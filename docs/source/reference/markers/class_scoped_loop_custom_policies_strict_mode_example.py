import asyncio

import pytest


@pytest.mark.asyncio_event_loop(
    policy=[
        asyncio.DefaultEventLoopPolicy(),
        asyncio.DefaultEventLoopPolicy(),
    ]
)
class TestWithDifferentLoopPolicies:
    @pytest.mark.asyncio
    async def test_parametrized_loop(self):
        pass
