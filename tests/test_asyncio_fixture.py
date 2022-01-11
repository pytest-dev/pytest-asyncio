import asyncio

import pytest

import pytest_asyncio


@pytest_asyncio.fixture
async def fixture_bare():
    await asyncio.sleep(0)
    return 1


@pytest.mark.asyncio
async def test_bare_fixture(fixture_bare):
    await asyncio.sleep(0)
    assert fixture_bare == 1


@pytest_asyncio.fixture(name="new_fixture_name")
async def fixture_with_name(request):
    await asyncio.sleep(0)
    return request.fixturename


@pytest.mark.asyncio
async def test_fixture_with_name(new_fixture_name):
    await asyncio.sleep(0)
    assert new_fixture_name == "new_fixture_name"


@pytest_asyncio.fixture(params=[2, 4])
async def fixture_with_params(request):
    await asyncio.sleep(0)
    return request.param


@pytest.mark.asyncio
async def test_fixture_with_params(fixture_with_params):
    await asyncio.sleep(0)
    assert fixture_with_params % 2 == 0
