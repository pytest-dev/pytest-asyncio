Avoid the unused port fixtures
==============================

The ``unused_tcp_port``, ``unused_tcp_port_factory``, ``unused_udp_port``, and
``unused_udp_port_factory`` fixtures are deprecated because the port they
return can be claimed by another process before the test binds it.

Bind to port 0 instead and read the port assigned by the operating system.

Migration
---------

Replace the fixtures with the patterns below:

- ``unused_tcp_port`` / ``unused_udp_port``: bind the server or datagram
  endpoint to port 0 and read the port assigned by the operating system.
  The examples below show the full pattern for TCP and UDP.
- ``unused_tcp_port_factory`` / ``unused_udp_port_factory``: create each
  server or datagram endpoint on port 0 and read its assigned port. If the
  port must be passed to another process before the server starts, bind the
  socket in the test and pass the listening socket (or use a
  ``socketpair``/pipe) instead of a bare port number; a bare port can always
  be claimed before the other process binds it.

The deprecated fixtures remain available and keep working, but they emit a
``DeprecationWarning``. The warning and this guide describe the same
migration; the guide exists because the fixtures are public API and the
warning alone does not show the replacement pattern.

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
