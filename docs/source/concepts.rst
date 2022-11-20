========
Concepts
========

asyncio event loops
===================
pytest-asyncio runs each test item in its own asyncio event loop. The loop can be accessed via the ``event_loop`` fixture, which is automatically requested by all async tests.

.. code-block:: python

    async def test_provided_loop_is_running_loop(event_loop):
        assert event_loop is asyncio.get_running_loop()

You can think of `event_loop` as an autouse fixture for async tests.

Test discovery modes
====================

Pytest-asyncio provides two modes for test discovery, *strict* and *auto*.


Strict mode
-----------

In strict mode pytest-asyncio will only run tests that have the *asyncio* marker and will only evaluate async fixtures decorated with ``@pytest_asyncio.fixture``. Test functions and fixtures without these markers and decorators will not be handled by pytest-asyncio.

This mode is intended for projects that want so support multiple asynchronous programming libraries as it allows pytest-asyncio to coexist with other async testing plugins in the same codebase.

Pytest automatically enables installed plugins. As a result pytest plugins need to coexist peacefully in their default configuration. This is why strict mode is the default mode.

Auto mode
---------

In *auto* mode pytest-asyncio automatically adds the *asyncio* marker to all asynchronous test functions. It will also take ownership of all async fixtures, regardless of whether they are decorated with ``@pytest.fixture`` or ``@pytest_asyncio.fixture``.

This mode is intended for projects that use *asyncio* as their only asynchronous programming library. Auto mode makes for the simplest test and fixture configuration and is the recommended default.

If you intend to support multiple asynchronous programming libraries, e.g. *asyncio* and *trio*, strict mode will be the preferred option.
