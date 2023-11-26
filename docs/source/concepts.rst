========
Concepts
========

asyncio event loops
===================
In order to understand how pytest-asyncio works, it helps to understand how pytest collectors work.
If you already know about pytest collectors, please :ref:`skip ahead <pytest-asyncio-event-loops>`.
Otherwise, continue reading.
Let's assume we have a test suite with a file named *test_all_the_things.py* holding a single test, async or not:

.. include:: concepts_function_scope_example.py
    :code: python

The file *test_all_the_things.py* is a Python module with a Python test function.
When we run pytest, the test runner descends into Python packages, modules, and classes, in order to find all tests, regardless whether the tests will run or not.
This process is referred to as *test collection* by pytest.
In our particular example, pytest will find our test module and the test function.
We can visualize the collection result by running ``pytest --collect-only``::

    <Module test_all_the_things.py>
      <Function test_runs_in_a_loop>

The example illustrates that the code of our test suite is hierarchical.
Pytest uses so called *collectors* for each level of the hierarchy.
Our contrived example test suite uses the *Module* and *Function* collectors, but real world test code may contain additional hierarchy levels via the *Package* or *Class* collectors.
There's also a special *Session* collector at the root of the hierarchy.
You may notice that the individual levels resemble the possible `scopes of a pytest fixture. <https://docs.pytest.org/en/7.4.x/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session>`__

.. _pytest-asyncio-event-loops:

Pytest-asyncio provides one asyncio event loop for each pytest collector.
By default, each test runs in the event loop provided by the *Function* collector, i.e. tests use the loop with the narrowest scope.
This gives the highest level of isolation between tests.
If two or more tests share a common ancestor collector, the tests can be configured to run in their ancestor's loop by passing the appropriate *scope* keyword argument to the *asyncio* mark.
For example, the following two tests use the asyncio event loop provided by the *Module* collector:

.. include:: concepts_module_scope_example.py
    :code: python

It's highly recommended for neighboring tests to use the same event loop scope.
For example, all tests in a class or module should use the same scope.
Assigning neighboring tests to different event loop scopes is discouraged as it can make test code hard to follow.

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
