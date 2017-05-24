import asyncio
import pytest


@pytest.mark.asyncio
@asyncio.coroutine
def test_dependent_fixture(dependent_fixture):
    """Test a dependent fixture."""
    yield from asyncio.sleep(0.1)
