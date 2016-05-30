import sys
import pytest
import asyncio
import concurrent.futures

collect_ignore = []
if sys.version_info[:2] < (3, 5):
    collect_ignore.append("test_simple_35.py")
    collect_ignore.append("test_async_fixture_35.py")


@pytest.yield_fixture
def loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def loop_process_pool(loop):
    loop.set_default_executor(concurrent.futures.ProcessPoolExecutor())
    return loop
