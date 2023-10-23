import asyncio

import pytest


class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    pass


@pytest.mark.asyncio_event_loop(policy=CustomEventLoopPolicy())
class TestUsesCustomEventLoopPolicy:
    @pytest.mark.asyncio
    async def test_uses_custom_event_loop_policy(self):
        assert isinstance(asyncio.get_event_loop_policy(), CustomEventLoopPolicy)
