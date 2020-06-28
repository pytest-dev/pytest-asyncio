"""Unit tests for overriding the event loop."""
import asyncio

import pytest


def test_execute_event_loop_policy_first(event_loop_policy):
    """This test assures event_loop_policy fixture is executed before event_loop fixture"""
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"


@pytest.mark.asyncio
async def test_for_custom_loop_policy():
    """This test should be executed using the custom loop."""
    await asyncio.sleep(0.01)
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"


@pytest.mark.asyncio
async def test_dependent_fixture(dependent_fixture):
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_for_custom_loop_policy_2():
    """This test should be executed using the custom loop."""
    await asyncio.sleep(0.01)
    assert type(asyncio.get_event_loop()).__name__ == "CustomSelectorLoop"
