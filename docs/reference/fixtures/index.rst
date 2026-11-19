========
Fixtures
========

unused_tcp_port
===============
Finds and yields a single unused TCP port on the localhost interface. Useful for
binding temporary test servers.

.. note::
    Deprecated. The returned port is released before the test runs, so another
    process can claim it before the test server starts. Bind port 0 instead
    and read the assigned port from the server socket, for example pass
    ``port=0`` to ``asyncio.start_server()`` and read
    ``server.sockets[0].getsockname()``.

unused_tcp_port_factory
=======================
A callable which returns a different unused TCP port each invocation. Useful
when several unused TCP ports are required in a test.

.. code-block:: python

    def a_test(unused_tcp_port_factory):
        _port1, _port2 = unused_tcp_port_factory(), unused_tcp_port_factory()

.. note::
    Deprecated. The returned ports are released before the test runs, so
    another process can claim them before the test server starts. Bind port 0
    instead and read the assigned port from the server socket, for example
    pass ``port=0`` to ``asyncio.start_server()`` and read
    ``server.sockets[0].getsockname()``.

unused_udp_port and unused_udp_port_factory
===========================================
Works just like their TCP counterparts but returns unused UDP ports.

.. note::
    Deprecated. The returned ports are released before the test runs, so
    another process can claim them before the test server starts. Bind port 0
    instead and read the assigned port from the transport, for example pass
    ``local_addr=("127.0.0.1", 0)`` to ``loop.create_datagram_endpoint()`` and
    read ``transport.get_extra_info("sockname")``. A subprocess can inherit an
    already-bound socket, or bind port 0 itself and report its address when
    ready.
