Avoid the unused port fixtures
==============================

The ``unused_tcp_port``, ``unused_tcp_port_factory``, ``unused_udp_port``, and
``unused_udp_port_factory`` fixtures are deprecated because the port they
return can be claimed by another process before the test binds it.

Bind to port 0 instead and read the port assigned by the operating system.

TCP
---

.. code-block:: python

    import asyncio

    import pytest


    async def handler(reader, writer):
        writer.close()


    @pytest.mark.asyncio
    async def test_server():
        server = await asyncio.start_server(handler, host="127.0.0.1", port=0)
        port = server.sockets[0].getsockname()[1]
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close()
            await writer.wait_closed()
        finally:
            server.close()
            await server.wait_closed()

UDP
---

.. code-block:: python

    import asyncio

    import pytest


    class Protocol(asyncio.DatagramProtocol):
        pass


    @pytest.mark.asyncio
    async def test_datagram_endpoint():
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            Protocol, local_addr=("127.0.0.1", 0)
        )
        port = transport.get_extra_info("sockname")[1]
        try:
            transport.sendto(b"ping", ("127.0.0.1", port))
        finally:
            transport.close()
