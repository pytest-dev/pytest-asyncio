========
Fixtures
========

unused_tcp_port
===============
Finds and yields a single unused TCP port on the localhost interface. Useful for
binding temporary test servers.

unused_tcp_port_factory
=======================
A callable which returns a different unused TCP port each invocation. Useful
when several unused TCP ports are required in a test.

.. code-block:: python

    def a_test(unused_tcp_port_factory):
        _port1, _port2 = unused_tcp_port_factory(), unused_tcp_port_factory()

unused_udp_port and unused_udp_port_factory
===========================================
Works just like their TCP counterparts but returns unused UDP ports.
