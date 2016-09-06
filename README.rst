pytest-asyncio: pytest support for asyncio
==========================================

.. image:: https://img.shields.io/pypi/v/pytest-asyncio.svg
    :target: https://pypi.python.org/pypi/pytest-asyncio
.. image:: https://travis-ci.org/pytest-dev/pytest-asyncio.svg?branch=master
    :target: https://travis-ci.org/pytest-dev/pytest-asyncio
.. image:: https://coveralls.io/repos/pytest-dev/pytest-asyncio/badge.svg
    :target: https://coveralls.io/r/pytest-dev/pytest-asyncio

pytest-asyncio is an Apache2 licensed library, written in Python, for testing
asyncio code with pytest.

asyncio code is usually written in the form of coroutines, which makes it
slightly more difficult to test using normal testing tools. pytest-asyncio
provides useful fixtures and markers to make testing easier.

.. code-block:: python

    @pytest.mark.asyncio
    async def test_some_asyncio_code():
        res = await library.do_something()
        assert b'expected result' == res

or, if you're using the pre-Python 3.5 syntax:

.. code-block:: python

    @pytest.mark.asyncio
    def test_some_asyncio_code():
        res = yield from library.do_something()
        assert b'expected result' == res

pytest-asyncio has been strongly influenced by pytest-tornado_.

.. _pytest-tornado: https://github.com/eugeniy/pytest-tornado

Features
--------

- fixtures for creating and injecting versions of the asyncio event loop
- fixtures for injecting unused tcp ports
- pytest markers for treating tests as asyncio coroutines
- easy testing with non-default event loops


Installation
------------

To install pytest-asyncio, simply:

.. code-block:: bash

    $ pip install pytest-asyncio

This is enough for pytest to pick up pytest-asyncio.

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

.. code-block:: python

    def test_http_client(event_loop):
        url = 'http://httpbin.org/get'
        resp = event_loop.run_until_complete(http_client(url))
        assert b'HTTP/1.1 200 OK' in resp

This fixture can be easily overridden in any of the standard pytest locations
(e.g. directly in the test file, or in ``conftest.py``) to use a non-default
event loop. This will take effect even if you're using the
``pytest.mark.asyncio`` marker and not the ``event_loop`` fixture directly.

.. code-block:: python

    @pytest.yield_fixture()
    def event_loop():
        loop = MyCustomLoop()
        yield loop
        loop.close()

A special pytest hook will ensure the produced loop is either set as the
default global loop, or a special, error-throwing event loop policy is installed
as the default policy (depending on the ``forbid_global_loop`` parameter).
Fixtures depending on the ``event_loop`` fixture can expect the policy to be
properly modified when they run.

``event_loop_process_pool``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``event_loop_process_pool`` fixture is almost identical to the
``event_loop`` fixture, except the created event loop will have a
``concurrent.futures.ProcessPoolExecutor`` set as the default executor.

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

Markers
-------

``pytest.mark.asyncio(forbid_global_loop=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Mark your test coroutine with this marker and pytest will execute it as an
asyncio task using the event loop provided by the ``event_loop`` fixture. See
the introductory section for an example.

The event loop used can be overriden by overriding the ``event_loop`` fixture
(see above).

If ``forbid_global_loop`` is true, ``asyncio.get_event_loop()`` will result
in exceptions, ensuring your tests are always passing the event loop explicitly.

``pytest.mark.asyncio_process_pool(forbid_global_loop=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``asyncio_process_pool`` marker is almost identical to the ``asyncio``
marker, except the event loop used will have a
``concurrent.futures.ProcessPoolExecutor`` set as the default executor.

Changelog
---------

0.5.0 (2016-09-07)
~~~~~~~~~~~~~~~~~~
- Introduced a changelog.
  `#31 <https://github.com/pytest-dev/pytest-asyncio/issues/31>`_
- The ``event_loop`` fixture is again responsible for closing itself.
  This makes the fixture slightly harder to correctly override, but enables
  other fixtures to depend on it correctly.
  `#30 <https://github.com/pytest-dev/pytest-asyncio/issues/30>`_
- Deal with the event loop policy by wrapping a special pytest hook,
  ``pytest_fixture_setup``. This allows setting the policy before fixtures
  dependent on the ``event_loop`` fixture run, thus allowing them to take
  advantage of the ``forbid_global_loop`` parameter. As a consequence of this,
  we now depend on pytest 3.0.
  `#29 <https://github.com/pytest-dev/pytest-asyncio/issues/29>`_


0.4.1 (2016-06-01)
~~~~~~~~~~~~~~~~~~
- Fix a bug preventing the propagation of exceptions from the plugin.
  `#25 <https://github.com/pytest-dev/pytest-asyncio/issues/25>`_

0.4.0 (2016-05-30)
~~~~~~~~~~~~~~~~~~
- Make ``event_loop`` fixtures simpler to override by closing them in the
  plugin, instead of directly in the fixture.
  `#21 <https://github.com/pytest-dev/pytest-asyncio/pull/21>`_
- Introduce the ``forbid_global_loop`` parameter.
  `#21 <https://github.com/pytest-dev/pytest-asyncio/pull/21>`_

0.3.0 (2015-12-19)
~~~~~~~~~~~~~~~~~~
- Support for Python 3.5 ``async``/``await`` syntax.
  `#17 <https://github.com/pytest-dev/pytest-asyncio/pull/17>`_

0.2.0 (2015-08-01)
~~~~~~~~~~~~~~~~~~
- ``unused_tcp_port_factory`` fixture.
  `#10 <https://github.com/pytest-dev/pytest-asyncio/issues/10>`_


0.1.1 (2015-04-23)
~~~~~~~~~~~~~~~~~~
Initial release.


Contributing
------------
Contributions are very welcome. Tests can be run with ``tox``, please ensure
the coverage at least stays the same before you submit a pull request.
