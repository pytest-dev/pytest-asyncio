import pytest_asyncio


@pytest_asyncio.fixture
async def fixture_runs_in_fresh_loop_for_every_function(): ...


@pytest_asyncio.fixture(loop_scope="session", scope="module")
async def fixture_runs_in_session_loop_once_per_module(): ...


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def fixture_runs_in_module_loop_once_per_module(): ...


@pytest_asyncio.fixture(loop_scope="module")
async def fixture_runs_in_module_loop_once_per_function(): ...
