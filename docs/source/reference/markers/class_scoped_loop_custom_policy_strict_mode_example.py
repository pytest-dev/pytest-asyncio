import asyncio

import pytest


class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    pass


@pytest.fixture(scope="class")
def event_loop_policy(request):
    return CustomEventLoopPolicy()


@pytest.mark.asyncio_event_loop
class TestUsesCustomEventLoopPolicy:
    @pytest.mark.asyncio
    async def test_uses_custom_event_loop_policy(self):
        assert isinstance(asyncio.get_event_loop_policy(), CustomEventLoopPolicy)
