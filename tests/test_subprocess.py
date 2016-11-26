"""Tests for using subprocesses in tests."""
import sys
import asyncio
import asyncio.subprocess

import pytest


@pytest.mark.asyncio(forbid_global_loop=False)
@asyncio.coroutine
def test_subprocess(event_loop):
    """Starting a subprocess should be possible."""
    proc = yield from asyncio.subprocess.create_subprocess_exec(
        sys.executable, '--version', stdout=asyncio.subprocess.PIPE,
        loop=event_loop)
    yield from proc.communicate()


@pytest.mark.asyncio(forbid_global_loop=True)
@asyncio.coroutine
def test_subprocess_forbid(event_loop):
    """Starting a subprocess should be possible."""
    proc = yield from asyncio.subprocess.create_subprocess_exec(
        sys.executable, '--version', stdout=asyncio.subprocess.PIPE,
        loop=event_loop)
    yield from proc.communicate()
