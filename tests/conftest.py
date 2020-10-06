import asyncio

import pytest


@pytest.fixture
def dependent_fixture(event_loop):
    """A fixture dependent on the event_loop fixture, doing some cleanup."""
    counter = 0

    async def just_a_sleep():
        """Just sleep a little while."""
        nonlocal event_loop
        await asyncio.sleep(0.1)
        nonlocal counter
        counter += 1

    event_loop.run_until_complete(just_a_sleep())
    yield
    event_loop.run_until_complete(just_a_sleep())

    assert counter == 2
