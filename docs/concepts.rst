========
Concepts
========

.. _concepts/event_loops:

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
If two or more tests share a common ancestor collector, the tests can be configured to run in their ancestor's loop by passing the appropriate *loop_scope* keyword argument to the *asyncio* mark.
For example, the following two tests use the asyncio event loop provided by the *Module* collector:

.. include:: concepts_module_scope_example.py
    :code: python

It's highly recommended for neighboring tests to use the same event loop scope.
For example, all tests in a class or module should use the same scope.
Assigning neighboring tests to different event loop scopes is discouraged as it can make test code hard to follow.

Test discovery modes
====================

Pytest-asyncio provides two modes for test discovery, *strict* and *auto*.
This can be set through Pytest's ``--asyncio-mode`` command line flag,
or through the configuration file.

.. tabs::

   .. group-tab:: Strict mode

      .. code-block:: toml

         [tool.pytest.ini_options]
         asyncio_mode = "strict"

      In strict mode pytest-asyncio will only run tests that have the *asyncio* marker
      and will only evaluate async fixtures decorated with ``@pytest_asyncio.fixture``.
      Test functions and fixtures without these markers and decorators will not be
      handled by pytest-asyncio.

      This mode is intended for projects that want to support multiple asynchronous
      programming libraries as it allows pytest-asyncio to coexist with other async
      testing plugins in the same codebase.

      Pytest automatically enables installed plugins. As a result pytest plugins
      need to coexist peacefully in their default configuration. This is why strict
      mode is the default mode.

   .. group-tab:: Auto mode

      .. code-block:: toml

         [tool.pytest.ini_options]
         asyncio_mode = "auto"

      In *auto* mode pytest-asyncio automatically adds the *asyncio* marker to all
      asynchronous test functions. It will also take ownership of all async fixtures,
      regardless of whether they are decorated with ``@pytest.fixture`` or
      ``@pytest_asyncio.fixture``.

      This mode is intended for projects that use *asyncio* as their only asynchronous
      programming library. Auto mode makes for the simplest test and fixture
      configuration and is the recommended default.

      If you intend to support multiple asynchronous programming libraries,
      e.g. *asyncio* and *trio*, strict mode will be the preferred option.

.. _concepts/concurrent_execution:

Test execution and concurrency
==============================

pytest-asyncio runs async tests sequentially, just like how pytest runs synchronous tests. Each asynchronous test runs within its assigned event loop. For example, consider the following two tests:

.. include:: concepts_concurrent_execution_example.py
    :code: python

This sequential execution is intentional and important for maintaining test isolation. Running tests concurrently could introduce race conditions and side effects where one test could interfere with another, making test results unreliable and difficult to debug.

.. _concepts/tasks:

Fixture tasks and cancellation
==============================

This section explains the experimental :ref:`asyncio_experimental_task_per_fixture <configuration/asyncio_experimental_task_per_fixture>` option.

By default, pytest-asyncio runs the setup of an async generator fixture, the code before ``yield``, in one asyncio task, and its teardown, the code after ``yield``, in another.
While tests use the fixture, no task runs it, so context managers around ``yield`` do not work as they do in ordinary asyncio code:

* If a background task in an ``asyncio.TaskGroup`` fails, the test is not stopped, and the fixture's teardown can hang while it waits for the group's other tasks.
* An ``asyncio.timeout()`` that expires does not stop the test, and no error is reported.

With the option enabled, each async fixture runs in an asyncio task of its own, from setup to teardown.
While tests use the fixture, its task waits at ``yield``, so context managers around ``yield`` are entered and exited in the same task, as in ordinary asyncio code.

For example, this fixture sets a one-second deadline, counted from its setup, for each async test that uses it:

.. include:: concepts_fixture_deadline_example.py
    :code: python

A task group or timeout stops the code inside it by *cancelling* the task that runs it: ``asyncio.CancelledError`` is raised where that task is waiting.
While tests use a fixture, its task is waiting at ``yield``, so the error would be raised there.
But the test and other fixtures are still using the fixture's value, and cleaning the fixture up immediately would close resources they depend on.
So pytest-asyncio handles the cancellation in two steps:

* It cancels the async test or fixture setup that is running, just as the task group or timeout would cancel code inside it.
* It raises the cancellation at the fixture's ``yield`` later, when pytest tears the fixture down, after the fixtures that depend on it.
  Context managers and ``finally`` blocks run, but other statements after ``yield`` are skipped unless the fixture handles the cancellation.
  The task group's or timeout's error is reported as an error at the fixture's teardown.

In the example, a test that takes longer than a second is cancelled, and pytest reports the timeout's ``TimeoutError`` at the fixture's teardown.
By default, the timeout has no effect: a slow test passes, and a test that waits for something that never happens hangs.

The :ref:`option's reference <configuration/asyncio_experimental_task_per_fixture>` gives the exact rules and limitations.
