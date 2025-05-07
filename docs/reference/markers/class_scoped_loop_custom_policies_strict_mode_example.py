import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from asyncio import DefaultEventLoopPolicy

import pytest


@pytest.fixture(
    params=[
        DefaultEventLoopPolicy(),
        DefaultEventLoopPolicy(),
    ]
)
def event_loop_policy(request):
    return request.param


class TestWithDifferentLoopPolicies:
    @pytest.mark.asyncio
    async def test_parametrized_loop(self):
        pass
