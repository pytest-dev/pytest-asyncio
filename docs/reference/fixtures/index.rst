========
Fixtures
========

event_loop_policy
=================
Returns the event loop policy used to create asyncio event loops.
The default return value is *asyncio.get_event_loop_policy().*

This fixture can be overridden when a different event loop policy should be used.

.. include:: event_loop_policy_example.py
    :code: python

Multiple policies can be provided via fixture parameters.
The fixture is automatically applied to all pytest-asyncio tests.
Therefore, all tests managed by pytest-asyncio are run once for each fixture parameter.
The following example runs the test with different event loop policies.

.. include:: event_loop_policy_parametrized_example.py
    :code: python

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
