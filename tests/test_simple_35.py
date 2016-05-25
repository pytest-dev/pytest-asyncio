"""Quick'n'dirty unit tests using async and await syntax."""
import asyncio

import pytest


@asyncio.coroutine
async def async_coro(loop):
    await asyncio.sleep(0, loop=loop)
    return 'ok'


@pytest.mark.asyncio
async def test_asyncio_marker(loop):
    """Test the asyncio pytest marker."""


@pytest.mark.asyncio
async def test_asyncio_marker_with_default_param(loop, a_param=None):
    """Test the asyncio pytest marker."""


@pytest.mark.asyncio
async def test_asyncio_process_pool(loop_process_pool):
    ret = await async_coro(loop_process_pool)
    assert ret == 'ok'


@pytest.mark.asyncio
async def test_unused_port_fixture(unused_tcp_port, loop):
    """Test the unused TCP port fixture."""
    async def closer(_, writer):
        writer.close()

    server1 = await asyncio.start_server(closer, host='localhost',
                                         port=unused_tcp_port,
                                         loop=loop)

    server1.close()
    await server1.wait_closed()


def test_unused_port_factory_fixture(unused_tcp_port_factory, loop):
    """Test the unused TCP port factory fixture."""

    async def closer(_, writer):
        writer.close()

    port1, port2, port3 = (unused_tcp_port_factory(), unused_tcp_port_factory(),
                           unused_tcp_port_factory())

    async def run_test():
        server1 = await asyncio.start_server(closer, host='localhost',
                                             port=port1,
                                             loop=loop)
        server2 = await asyncio.start_server(closer, host='localhost',
                                             port=port2,
                                             loop=loop)
        server3 = await asyncio.start_server(closer, host='localhost',
                                             port=port3,
                                             loop=loop)

        for port in port1, port2, port3:
            with pytest.raises(IOError):
                await asyncio.start_server(closer, host='localhost',
                                            port=port,
                                            loop=loop)

        server1.close()
        await server1.wait_closed()
        server2.close()
        await server2.wait_closed()
        server3.close()
        await server3.wait_closed()

    loop.run_until_complete(run_test())

    loop.stop()
    loop.close()


class Test:
    """Test that asyncio marked functions work in test methods."""

    @pytest.mark.asyncio
    async def test_asyncio_marker_method(self, loop):
        """Test the asyncio pytest marker in a Test class."""
        ret = await async_coro(loop)
        assert ret == 'ok'


def test_async_close_loop(loop):
    loop.close()
    return 'ok'
