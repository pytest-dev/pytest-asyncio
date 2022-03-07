pytest-asyncio: pytest support for asyncio
==========================================

.. image:: https://img.shields.io/pypi/v/pytest-asyncio.svg
    :target: https://pypi.python.org/pypi/pytest-asyncio
.. image:: https://github.com/pytest-dev/pytest-asyncio/workflows/CI/badge.svg
    :target: https://github.com/pytest-dev/pytest-asyncio/actions?workflow=CI
.. image:: https://codecov.io/gh/pytest-dev/pytest-asyncio/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/pytest-dev/pytest-asyncio
.. image:: https://img.shields.io/pypi/pyversions/pytest-asyncio.svg
    :target: https://github.com/pytest-dev/pytest-asyncio
    :alt: Supported Python versions
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

pytest-asyncio is an Apache2 licensed library, written in Python, for testing
asyncio code with pytest.

asyncio code is usually written in the form of coroutines, which makes it
slightly more difficult to test using normal testing tools. pytest-asyncio
provides useful fixtures and markers to make testing easier.

.. code-block:: python

    @pytest.mark.asyncio
    async def test_some_asyncio_code():
        res = await library.do_something()
        assert b"expected result" == res

pytest-asyncio has been strongly influenced by pytest-tornado_.

.. _pytest-tornado: https://github.com/eugeniy/pytest-tornado

Features
--------

- fixtures for creating and injecting versions of the asyncio event loop
- fixtures for injecting unused tcp/udp ports
- pytest markers for treating tests as asyncio coroutines
- easy testing with non-default event loops
- support for `async def` fixtures and async generator fixtures
- support *auto* mode to handle all async fixtures and tests automatically by asyncio;
  provide *strict* mode if a test suite should work with different async frameworks
  simultaneously, e.g. ``asyncio`` and ``trio``.

Installation
------------

To install pytest-asyncio, simply:

.. code-block:: bash

    $ pip install pytest-asyncio

This is enough for pytest to pick up pytest-asyncio.

Modes
-----

Starting from ``pytest-asyncio>=0.17``, three modes are provided: *auto*, *strict* and
*legacy* (default).

The mode can be set by ``asyncio_mode`` configuration option in `configuration file
<https://docs.pytest.org/en/latest/reference/customize.html>`_:

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_mode = auto

The value can be overridden by command-line option for ``pytest`` invocation:

.. code-block:: bash

   $ pytest tests --asyncio-mode=strict

Auto mode
~~~~~~~~~

When the mode is auto, all discovered *async* tests are considered *asyncio-driven* even
if they have no ``@pytest.mark.asyncio`` marker.

All async fixtures are considered *asyncio-driven* as well, even if they are decorated
with a regular ``@pytest.fixture`` decorator instead of dedicated
``@pytest_asyncio.fixture`` counterpart.

*asyncio-driven* means that tests and fixtures are executed by ``pytest-asyncio``
plugin.

This mode requires the simplest tests and fixtures configuration and is
recommended for default usage *unless* the same project and its test suite should
execute tests from different async frameworks, e.g. ``asyncio`` and ``trio``.  In this
case, auto-handling can break tests designed for other framework; please use *strict*
mode instead.

Strict mode
~~~~~~~~~~~

Strict mode enforces ``@pytest.mark.asyncio`` and ``@pytest_asyncio.fixture`` usage.
Without these markers, tests and fixtures are not considered as *asyncio-driven*, other
pytest plugin can handle them.

Please use this mode if multiple async frameworks should be combined in the same test
suite.


Legacy mode
~~~~~~~~~~~

This mode follows rules used by ``pytest-asyncio<0.17``: tests are not auto-marked but
fixtures are.

This mode is used by default for the sake of backward compatibility, deprecation
warnings are emitted with suggestion to either switching to ``auto`` mode or using
``strict`` mode with ``@pytest_asyncio.fixture`` decorators.

In future, the default will be changed.


Fixtures
--------

``event_loop``
~~~~~~~~~~~~~~
Creates and injects a new instance of the default asyncio event loop. By
default, the loop will be closed at the end of the test (i.e. the default
fixture scope is ``function``).

Note that just using the ``event_loop`` fixture won't make your test function
a coroutine. You'll need to interact with the event loop directly, using methods
like ``event_loop.run_until_complete``. See the ``pytest.mark.asyncio`` marker
for treating test functions like coroutines.

Simply using this fixture will not set the generated event loop as the
default asyncio event loop, or change the asyncio event loop policy in any way.
Use ``pytest.mark.asyncio`` for this purpose.

.. code-block:: python

    def test_http_client(event_loop):
        url = "http://httpbin.org/get"
        resp = event_loop.run_until_complete(http_client(url))
        assert b"HTTP/1.1 200 OK" in resp

This fixture can be easily overridden in any of the standard pytest locations
(e.g. directly in the test file, or in ``conftest.py``) to use a non-default
event loop. This will take effect even if you're using the
``pytest.mark.asyncio`` marker and not the ``event_loop`` fixture directly.

.. code-block:: python

    @pytest.fixture
    def event_loop():
        loop = MyCustomLoop()
        yield loop
        loop.close()

If the ``pytest.mark.asyncio`` marker is applied, a pytest hook will
ensure the produced loop is set as the default global loop.
Fixtures depending on the ``event_loop`` fixture can expect the policy to be properly modified when they run.

``unused_tcp_port``
~~~~~~~~~~~~~~~~~~~
Finds and yields a single unused TCP port on the localhost interface. Useful for
binding temporary test servers.

``unused_tcp_port_factory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
A callable which returns a different unused TCP port each invocation. Useful
when several unused TCP ports are required in a test.

.. code-block:: python

    def a_test(unused_tcp_port_factory):
        port1, port2 = unused_tcp_port_factory(), unused_tcp_port_factory()
        ...

``unused_udp_port`` and ``unused_udp_port_factory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Work just like their TCP counterparts but return unused UDP ports.


Async fixtures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

*auto* and *legacy* mode automatically converts async fixtures declared with the
standard ``@pytest.fixture`` decorator to *asyncio-driven* versions.


Markers
-------

``pytest.mark.asyncio``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Mark your test coroutine with this marker and pytest will execute it as an
asyncio task using the event loop provided by the ``event_loop`` fixture. See
the introductory section for an example.

The event loop used can be overridden by overriding the ``event_loop`` fixture
(see above).

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

Note about unittest
-------------------

Test classes subclassing the standard `unittest <https://docs.python.org/3/library/unittest.html>`__ library are not supported, users
are recommended to use `unitest.IsolatedAsyncioTestCase <https://docs.python.org/3/library/unittest.html#unittest.IsolatedAsyncioTestCase>`__
or an async framework such as `asynctest <https://asynctest.readthedocs.io/en/latest>`__.

Contributing
------------
Contributions are very welcome. Tests can be run with ``tox``, please ensure
the coverage at least stays the same before you submit a pull request.
