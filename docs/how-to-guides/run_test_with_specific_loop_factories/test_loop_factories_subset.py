import pytest


@pytest.mark.asyncio
async def test_runs_with_every_configured_factory():
    pass


@pytest.mark.asyncio(loop_factories=["custom"])
async def test_runs_with_only_custom_factory():
    pass
