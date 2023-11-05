========
Fixtures
========

event_loop
==========
Creates a new asyncio event loop based on the current event loop policy. The new loop
is available as the return value of this fixture for synchronous functions, or via `asyncio.get_running_loop <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_running_loop>`__ for asynchronous functions.
The event loop is closed when the fixture scope ends.
The fixture scope defaults to ``function`` scope.

.. include:: event_loop_example.py
    :code: python

Note that, when using the ``event_loop`` fixture, you need to interact with the event loop using methods like ``event_loop.run_until_complete``. If you want to *await* code inside your test function, you need to write a coroutine and use it as a test function. The `asyncio <#pytest-mark-asyncio>`__ marker
is used to mark coroutines that should be treated as test functions.

If you need to change the type of the event loop, prefer setting a custom event loop policy over redefining the ``event_loop`` fixture.

If the ``pytest.mark.asyncio`` decorator is applied to a test function, the ``event_loop``
fixture will be requested automatically by the test function.

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
        port1, port2 = unused_tcp_port_factory(), unused_tcp_port_factory()
        ...

unused_udp_port and unused_udp_port_factory
===========================================
Works just like their TCP counterparts but returns unused UDP ports.
