"""Tests for using subprocesses in tests."""

from __future__ import annotations

import asyncio.subprocess
import sys

import pytest


@pytest.mark.asyncio
async def test_subprocess():
    """Starting a subprocess should be possible."""
    proc = await asyncio.subprocess.create_subprocess_exec(
        sys.executable, "--version", stdout=asyncio.subprocess.PIPE
    )
    await proc.communicate()
