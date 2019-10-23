"""Quick'n'dirty unit tests for provided fixtures and markers."""
import asyncio
import os
import sys
import pytest


async def async_coro():
    await asyncio.sleep(0)
    return 'ok'


def test_event_loop_fixture(event_loop):
    """Test the injection of the event_loop fixture."""
    assert event_loop
    ret = event_loop.run_until_complete(async_coro())
    assert ret == 'ok'


@pytest.mark.skipif(
    sys.version_info >= (3, 7),
    reason="Default process poll executor is deprecated since Python 3.8"
)
def test_event_loop_processpool_fixture(event_loop_process_pool):
    """Test the injection of the event_loop with a process pool fixture."""
    assert event_loop_process_pool

    ret = event_loop_process_pool.run_until_complete(
        async_coro())
    assert ret == 'ok'

    this_pid = os.getpid()
    future = event_loop_process_pool.run_in_executor(None, os.getpid)
    pool_pid = event_loop_process_pool.run_until_complete(future)
    assert this_pid != pool_pid


@pytest.mark.asyncio
async def test_asyncio_marker():
    """Test the asyncio pytest marker."""
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_asyncio_marker_with_default_param(a_param=None):
    """Test the asyncio pytest marker."""
    await asyncio.sleep(0)


@pytest.mark.skipif(
    sys.version_info >= (3, 7),
    reason="Default process poll executor is deprecated since Python 3.8"
)
@pytest.mark.asyncio_process_pool
async def test_asyncio_process_pool_marker(event_loop):
    """Test the asyncio pytest marker."""
    ret = await async_coro()
    assert ret == 'ok'


@pytest.mark.asyncio
async def test_unused_port_fixture(unused_tcp_port, event_loop):
    """Test the unused TCP port fixture."""

    async def closer(_, writer):
        writer.close()

    server1 = await asyncio.start_server(closer, host='localhost',
                                         port=unused_tcp_port)

    with pytest.raises(IOError):
        await asyncio.start_server(closer, host='localhost',
                                   port=unused_tcp_port)

    server1.close()
    await server1.wait_closed()


class Test:
    """Test that asyncio marked functions work in test methods."""

    @pytest.mark.asyncio
    async def test_asyncio_marker_method(self, event_loop):
        """Test the asyncio pytest marker in a Test class."""
        ret = await async_coro()
        assert ret == 'ok'
