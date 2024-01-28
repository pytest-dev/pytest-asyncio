"""Tests for using subprocesses in tests."""

import asyncio.subprocess
import sys

import pytest

if sys.platform == "win32":
    # The default asyncio event loop implementation on Windows does not
    # support subprocesses. Subprocesses are available for Windows if a
    # ProactorEventLoop is used.
    @pytest.fixture()
    def event_loop():
        loop = asyncio.ProactorEventLoop()
        yield loop
        loop.close()


@pytest.mark.asyncio
async def test_subprocess():
    """Starting a subprocess should be possible."""
    proc = await asyncio.subprocess.create_subprocess_exec(
        sys.executable, "--version", stdout=asyncio.subprocess.PIPE
    )
    await proc.communicate()
