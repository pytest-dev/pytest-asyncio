=========
Reference
=========

Configuration
=============

The pytest-asyncio mode can be set by the ``asyncio_mode`` configuration option in the `configuration file
<https://docs.pytest.org/en/latest/reference/customize.html>`_:

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_mode = auto

The value can also be set via the ``--asyncio-mode`` command-line option:

.. code-block:: bash

   $ pytest tests --asyncio-mode=strict


If the asyncio mode is set in both the pytest configuration file and the command-line option, the command-line option takes precedence. If no asyncio mode is specified, the mode defaults to `strict`.

Fixtures
========

``event_loop``
--------------
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

    @pytest.fixture(scope="session")
    def event_loop():
        policy = asyncio.get_event_loop_policy()
        loop = policy.new_event_loop()
        yield loop
        loop.close()

If you need to change the type of the event loop, prefer setting a custom event loop policy over redefining the ``event_loop`` fixture.

If the ``pytest.mark.asyncio`` decorator is applied to a test function, the ``event_loop``
fixture will be requested automatically by the test function.

``unused_tcp_port``
-------------------
Finds and yields a single unused TCP port on the localhost interface. Useful for
binding temporary test servers.

``unused_tcp_port_factory``
---------------------------
A callable which returns a different unused TCP port each invocation. Useful
when several unused TCP ports are required in a test.

.. code-block:: python

    def a_test(unused_tcp_port_factory):
        port1, port2 = unused_tcp_port_factory(), unused_tcp_port_factory()
        ...

``unused_udp_port`` and ``unused_udp_port_factory``
---------------------------------------------------
Works just like their TCP counterparts but returns unused UDP ports.


Markers
=======

``pytest.mark.asyncio``
-----------------------
A coroutine or async generator with this marker will be treated as a test function by pytest. The marked function will be executed as an
asyncio task in the event loop provided by the ``event_loop`` fixture.

In order to make your test code a little more concise, the pytest |pytestmark|_
feature can be used to mark entire modules or classes with this marker.
Only test coroutines will be affected (by default, coroutines prefixed by
``test_``), so, for example, fixtures are safe to define.

.. code-block:: python

    import asyncio

    import pytest

    # All test coroutines will be treated as marked.
    pytestmark = pytest.mark.asyncio


    async def test_example(event_loop):
        """No marker!"""
        await asyncio.sleep(0, loop=event_loop)

In *auto* mode, the ``pytest.mark.asyncio`` marker can be omitted, the marker is added
automatically to *async* test functions.


.. |pytestmark| replace:: ``pytestmark``
.. _pytestmark: http://doc.pytest.org/en/latest/example/markers.html#marking-whole-classes-or-modules


Decorators
==========
Asynchronous fixtures are defined just like ordinary pytest fixtures, except they should be decorated with ``@pytest_asyncio.fixture``.

.. code-block:: python3

    import pytest_asyncio


    @pytest_asyncio.fixture
    async def async_gen_fixture():
        await asyncio.sleep(0.1)
        yield "a value"


    @pytest_asyncio.fixture(scope="module")
    async def async_fixture():
        return await asyncio.sleep(0.1)

All scopes are supported, but if you use a non-function scope you will need
to redefine the ``event_loop`` fixture to have the same or broader scope.
Async fixtures need the event loop, and so must have the same or narrower scope
than the ``event_loop`` fixture.

*auto* mode automatically converts async fixtures declared with the
standard ``@pytest.fixture`` decorator to *asyncio-driven* versions.
