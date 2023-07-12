========
Fixtures
========

event_loop
==========
Creates a new asyncio event loop based on the current event loop policy. The new loop
is available as the return value of this fixture or via `asyncio.get_running_loop <https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_running_loop>`__.
The event loop is closed when the fixture scope ends. The fixture scope defaults
to ``function`` scope.

.. code-block:: python

    def test_http_client(event_loop):
        url = "http://httpbin.org/get"
        resp = event_loop.run_until_complete(http_client(url))
        assert b"HTTP/1.1 200 OK" in resp

Note that, when using the ``event_loop`` fixture, you need to interact with the event loop using methods like ``event_loop.run_until_complete``. If you want to *await* code inside your test function, you need to write a coroutine and use it as a test function. The `asyncio <#pytest-mark-asyncio>`__ marker
is used to mark coroutines that should be treated as test functions.

The ``event_loop`` fixture can be overridden in any of the standard pytest locations,
e.g. directly in the test file, or in ``conftest.py``. This allows redefining the
fixture scope, for example:

.. code-block:: python

    @pytest.fixture(scope="module")
    def event_loop():
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        yield loop
        loop.close()

When defining multiple ``event_loop`` fixtures, you should ensure that their scopes don't overlap.
Each of the fixtures replace the running event loop, potentially without proper clean up.
This will emit a warning and likely lead to errors in your tests suite.
You can manually check for overlapping ``event_loop`` fixtures by running pytest with the ``--setup-show`` option.

If you need to change the type of the event loop, prefer setting a custom event loop policy over redefining the ``event_loop`` fixture.

If the ``pytest.mark.asyncio`` decorator is applied to a test function, the ``event_loop``
fixture will be requested automatically by the test function.

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
