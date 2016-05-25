pytest-asyncio: pytest support for asyncio
==========================================

.. image:: https://travis-ci.org/malinoff/pytest-asyncio.svg?branch=master
    :target: https://travis-ci.org/malinoff/pytest-asyncio

pytest-asyncio is an Apache2 licensed library, written in Python, for testing
asyncio code with pytest.

asyncio code is usually written in the form of coroutines, which makes it
slightly more difficult to test using normal testing tools. pytest-asyncio
provides useful fixtures and markers to make testing easier.

Original readme can be found in original `pytest-asyncio`_ repository.

This fork completely changes how ``pytest-asyncio`` works with coroutine-based
tests and loops:

    * No more closing the loop after each test coroutine function. It's up
      to the developer to choose when the loop is closed.

    * The use of global event loop is now forbidden by default. You can accept
      it by providing ``accept_global_loop=True`` to ``@asyncio.mark.asyncio``

    * No more implicit loops defined by the plugin. In order to use a loop,
      you must explicitly create and request ``loop`` fixture, otherwise
      the plugin will raise a ``MissingLoopFixture`` exception. This fixture
      can be named anything, but requires to return an instance of
      ``asyncio.AbstractEventLoop``. There is one exception: if
      ``accept_global_loop`` is ``True`` AND a ``loop`` fixture is not requested,
      the plugin will use the global loop.

The advantages are:

    * You do not rely on implicit event loops created by the plugin.
      Want to use ``concurrent.futures.ThreadPoolExecutor``? Easy!

      .. code-block:: python

          @pytest.yield_fixture
          def threadpooled_loop():
              loop = asyncio.get_event_loop_policy().new_event_loop()
              loop.set_default_executor(concurrent.futures.ThreadPoolExecutor())
              yield loop
              loop.close()

    * Lifetimes of loop fixtures can be expanded to ``module`` or ``session``
      scopes easily (in the original plugin it is not possible because the loop
      closes after each test coroutine function):

      .. code-block:: python
    
          @pytest.yield_fixture(scope='module')
          def loop():
              ...

Examples compared to the original examples:

.. code-block:: python

    # Original
    @pytest.mark.asyncio
    async def test_some_asyncio_code():
        res = await library.do_something()
        assert b'expected result' == res

    # Fork
    import asyncio
    @pytest.yield_fixture
    def loop():
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    @pytest.mark.asyncio
    async def test_some_asyncio_code(loop):
        res = await library.do_something(loop=loop)
        assert b'expected result' == res

or, if you're using the pre-Python 3.5 syntax:

.. code-block:: python

    # Original
    @pytest.mark.asyncio
    def test_some_asyncio_code():
        res = yield from library.do_something()
        assert b'expected result' == res

    # Fork
    import asyncio
    @pytest.fixture
    def loop():
        return asyncio.get_event_loop_policy().new_event_loop()

    @pytest.mark.asyncio
    async def test_some_asyncio_code(loop):
        res = await library.do_something(loop=loop)
        assert b'expected result' == res

pytest-asyncio has been strongly influenced by pytest-tornado_.

.. _pytest-asyncio: https://github.com/pytest-dev/pytest-asyncio/blob/master/README.rst
.. _pytest-tornado: https://github.com/eugeniy/pytest-tornado

Features
--------

- pluggable fixtures of the asyncio event loops
- fixtures for injecting unused tcp ports
- pytest markers for treating tests as asyncio coroutines
- easy testing with non-default event loops


Installation
------------

To install pytest-asyncio, simply:

.. code-block:: bash

    $ pip install git+https://github.com/malinoff/pytest-asyncio

This is enough for pytest to pick up pytest-asyncio.

Fixtures
--------

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

``pytest.mark.asyncio(accept_global_loop=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Mark your test coroutine with this marker and pytest will execute it as an
asyncio task using the event loop provided by a ``loop`` fixture. See
the introductory section for an example.

A different event loop can be provided easily, see the introductory section.

If ``accept_global_loop`` is false, ``asyncio.get_event_loop()`` will result
in exceptions, ensuring your tests are always passing the event loop explicitly.

Contributing
------------
Contributions are very welcome. Tests can be run with ``tox``, please ensure
the coverage at least stays the same before you submit a pull request.
