"""Tests for using subprocesses in tests."""
import sys
import asyncio
import asyncio.subprocess

import pytest


@pytest.mark.asyncio(forbid_global_loop=False)
async def test_subprocess(event_loop):
    """Starting a subprocess should be possible."""
    proc = await asyncio.subprocess.create_subprocess_exec(
        sys.executable, '--version', stdout=asyncio.subprocess.PIPE,
        loop=event_loop)
    await proc.communicate()


@pytest.mark.asyncio(forbid_global_loop=True)
async def test_subprocess_forbid(event_loop):
    """Starting a subprocess should be possible."""
    proc = await asyncio.subprocess.create_subprocess_exec(
        sys.executable, '--version', stdout=asyncio.subprocess.PIPE,
        loop=event_loop)
    await proc.communicate()
