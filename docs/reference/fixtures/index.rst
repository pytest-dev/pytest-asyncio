========
Fixtures
========

unused_tcp_port
===============
.. deprecated:: 1.6.0
    The ``unused_tcp_port`` fixture is deprecated due to inherent race conditions.
    The port is not reserved with the operating system and may be claimed by another
    process before the intended server binds to it.

    Instead of pre-allocating a port, configure the server or socket to bind
    directly to port 0 (e.g. using ``server = await asyncio.start_server(..., port=0)``
    or configuring an external server to bind to port 0) and query the socket
    for its assigned port via ``server.sockets[0].getsockname()[1]``. For
    subprocesses, either configure the child process to bind to port 0 and report
    its assigned address, or pre-bind a socket to port 0 and pass the socket or
    file descriptor to the child process.

Finds and yields a single unused TCP port on the localhost interface. Useful for
binding temporary test servers.

unused_tcp_port_factory
=======================
.. deprecated:: 1.6.0
    The ``unused_tcp_port_factory`` fixture is deprecated due to inherent race
    conditions. The factory's internal bookkeeping cannot reserve ports with the
    operating system. Bind directly to port 0 instead and retrieve the assigned
    port from the socket.

A callable which returns a different unused TCP port each invocation. Useful
when several unused TCP ports are required in a test.

.. code-block:: python

    def a_test(unused_tcp_port_factory):
        _port1, _port2 = unused_tcp_port_factory(), unused_tcp_port_factory()

unused_udp_port and unused_udp_port_factory
===========================================
.. deprecated:: 1.6.0
    The ``unused_udp_port`` and ``unused_udp_port_factory`` fixtures are deprecated
    due to inherent race conditions. For UDP, pass ``local_addr=("127.0.0.1", 0)`` to
    ``loop.create_datagram_endpoint()`` and read the assigned port using
    ``transport.get_extra_info("sockname")[1]``.

Works just like their TCP counterparts but returns unused UDP ports.
