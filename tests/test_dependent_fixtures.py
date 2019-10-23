import asyncio
import pytest


@pytest.mark.asyncio
async def test_dependent_fixture(dependent_fixture):
    """Test a dependent fixture."""
    await asyncio.sleep(0.1)
