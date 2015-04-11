pytest-asyncio: pytest support for asyncio
==========================================

.. image:: https://img.shields.io/pypi/v/pytest-asyncio.svg
    :target: https://pypi.python.org/pypi/pytest-asyncio
.. image:: https://travis-ci.org/Tinche/pytest-asyncio.svg?branch=master
    :target: https://travis-ci.org/Tinche/pytest-asyncio
.. image:: https://coveralls.io/repos/Tinche/pytest-asyncio/badge.svg?branch=master
    :target: https://coveralls.io/r/Tinche/pytest-asyncio?branch=master

pytest-asyncio is an Apache2 licensed library, written in Python, for testing
asyncio code with pytest.

asyncio code is usually written in the form of coroutines, which makes it
slightly more difficult to test using normal testing tools. pytest-asyncio
provides useful fixtures and markers to make testing easier.

.. code-block:: python

    @pytest.mark.asyncio
    def test_some_asyncio_code()
        res = yield from library.do_something()
        assert b'expected result' == res

pytest-asyncio has been strongly influenced by pytest-tornado_.

.. _pytest-tornado: https://github.com/eugeniy/pytest-tornado

Features
--------

- fixtures for creating and injecting versions of the asyncio event loop
- pytest markers for treating tests as asyncio coroutines


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
Creates and injects a new instance of the default asyncio event loop. The loop
will be closed at the end of the test.

Note that just using the ``event_loop`` fixture won't make your test function
a coroutine. You'll need to interact with the event loop directly, using methods
like ``event_loop.run_until_complete``. See the ``pytest.mark.asyncio`` marker
for treating test functions like coroutines.

.. code-block:: python

    def test_http_client(event_loop):
        url = 'http://httpbin.org/get'
        resp = event_loop.run_until_complete(http_client(url))
        assert b'HTTP/1.1 200 OK' in resp

``event_loop_process_pool``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``event_loop_process_pool`` fixture is almost identical to the
``event_loop`` fixture, except the created event loop will have a
``concurrent.futures.ProcessPoolExecutor`` set as the default executor.

``unused_tcp_port``
~~~~~~~~~~~~~~~~~~~
Finds and yields an unused TCP port on the localhost interface. Useful for
binding temporary test servers.

Markers
-------

``pytest.mark.asyncio``
~~~~~~~~~~~~~~~~~~~~~~~
Mark your test coroutine with this marker and pytest will execute it as an
asyncio task using the event loop provided by the ``event_loop`` fixture. See
the introductory section for an example.

``pytest.mark.asyncio_process_pool``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``asyncio_process_pool`` marker is almost identical to the ``asyncio``
marker, except the event loop used will have a
``concurrent.futures.ProcessPoolExecutor`` set as the default executor.


Contributing
------------
Contributions are very welcome. Tests can be run with ``tox``, please ensure
the coverage at least stays the same before you submit a pull request.
