import asyncio
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from asyncio import DefaultEventLoopPolicy

import pytest


class CustomEventLoopPolicy(DefaultEventLoopPolicy):
    pass


@pytest.fixture(
    params=(
        DefaultEventLoopPolicy(),
        CustomEventLoopPolicy(),
    ),
)
def event_loop_policy(request):
    return request.param


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
async def test_uses_custom_event_loop_policy():
    assert isinstance(asyncio.get_event_loop_policy(), DefaultEventLoopPolicy)
