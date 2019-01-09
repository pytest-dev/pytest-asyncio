"""Quick'n'dirty unit tests using async and await syntax."""
import asyncio

import pytest


@pytest.mark.asyncio
async def async_coro(loop):
    await asyncio.sleep(0, loop=loop)
    return 'ok'


@pytest.mark.asyncio
async def test_asyncio_marker():
    """Test the asyncio pytest marker."""


@pytest.mark.asyncio
async def test_asyncio_marker_with_default_param(a_param=None):
    """Test the asyncio pytest marker."""


@pytest.mark.asyncio
async def test_unused_port_fixture(unused_tcp_port, event_loop):
    """Test the unused TCP port fixture."""
    async def closer(_, writer):
        writer.close()

    server1 = await asyncio.start_server(closer, host='localhost',
                                         port=unused_tcp_port,
                                         loop=event_loop)

    server1.close()
    await server1.wait_closed()


def test_unused_port_factory_fixture(unused_tcp_port_factory, event_loop):
    """Test the unused TCP port factory fixture."""

    async def closer(_, writer):
        writer.close()

    port1, port2, port3 = (unused_tcp_port_factory(), unused_tcp_port_factory(),
                           unused_tcp_port_factory())

    async def run_test():
        server1 = await asyncio.start_server(closer, host='localhost',
                                             port=port1,
                                             loop=event_loop)
        server2 = await asyncio.start_server(closer, host='localhost',
                                             port=port2,
                                             loop=event_loop)
        server3 = await asyncio.start_server(closer, host='localhost',
                                             port=port3,
                                             loop=event_loop)

        for port in port1, port2, port3:
            with pytest.raises(IOError):
                await asyncio.start_server(closer, host='localhost',
                                           port=port,
                                           loop=event_loop)

        server1.close()
        await server1.wait_closed()
        server2.close()
        await server2.wait_closed()
        server3.close()
        await server3.wait_closed()

    event_loop.run_until_complete(run_test())

    event_loop.stop()
    event_loop.close()


class Test:
    """Test that asyncio marked functions work in test methods."""

    @pytest.mark.asyncio
    async def test_asyncio_marker_method(self, event_loop):
        """Test the asyncio pytest marker in a Test class."""
        ret = await async_coro(event_loop)
        assert ret == 'ok'


def test_async_close_loop(event_loop):
    event_loop.close()
    return 'ok'


@pytest.mark.asyncio_clock
async def test_mark_asyncio_clock():
    """
    Test that coroutines marked with asyncio_clock are run with a ClockEventLoop
    """
    assert hasattr(asyncio.get_event_loop(), 'advance_time')


def test_clock_loop_loop_fixture(clock_event_loop):
    """
    Test that the clock_event_loop fixture returns a proper instance of the loop
    """
    assert hasattr(asyncio.get_event_loop(), 'advance_time')
    clock_event_loop.close()
    return 'ok'


@pytest.mark.asyncio_clock
async def test_clock_loop_advance_time(clock_event_loop):
    """
    Test the sliding time event loop fixture
    """
    # a timeout for operations using advance_time
    NAP_TIME = 10

    # create the task
    task = clock_event_loop.create_task(asyncio.sleep(NAP_TIME))
    assert not task.done()

    # start the task
    await clock_event_loop.advance_time(0)
    assert not task.done()

    # process the timeout
    await clock_event_loop.advance_time(NAP_TIME)
    assert task.done()
