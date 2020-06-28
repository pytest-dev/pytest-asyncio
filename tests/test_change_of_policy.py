import asyncio
import pytest


@pytest.fixture(scope="module")
def old_policy():
    policy = asyncio.get_event_loop_policy()
    yield policy



@pytest.mark.asyncio
async def test_1(old_policy):
    assert old_policy == asyncio.get_event_loop_policy()

@pytest.mark.asyncio
async def test_2(old_policy):
    # This test fails with pytest-asyncio V0.14
    # due to a teardown change of event loop policy
    assert old_policy == asyncio.get_event_loop_policy()
