import pytest


@pytest.mark.asyncio
async def test_runs_with_default_factory_only():
    pass


@pytest.mark.asyncio
async def test_runs_with_custom_factory_only(requires_custom_loop):
    pass
