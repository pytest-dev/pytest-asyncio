"""Test the event loop fixture is properly disposed of.

These tests need to be run together.
"""
import asyncio
import pytest


def test_1():
    loop = asyncio.get_event_loop()
    assert not loop.is_closed()


@pytest.mark.asyncio
async def test_2():
    pass


def test_3():
    loop = asyncio.get_event_loop()
    assert not loop.is_closed()
