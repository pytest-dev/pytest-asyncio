import asyncio
import pytest


@pytest.fixture(autouse=True)
def loop(loop):
    return loop


@pytest.mark.asyncio
def test_autoused_loop():
    yield  # sleep(0)
