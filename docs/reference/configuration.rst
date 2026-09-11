=============
Configuration
=============

.. _configuration/asyncio_default_fixture_loop_scope:

asyncio_default_fixture_loop_scope
==================================
Determines the default event loop scope of asynchronous fixtures. When this configuration option is unset, it defaults to the fixture scope. In future versions of pytest-asyncio, the value will default to ``function`` when unset. Possible values are: ``function``, ``class``, ``module``, ``package``, ``session``

.. _configuration/asyncio_default_test_loop_scope:

asyncio_default_test_loop_scope
===============================
Determines the default event loop scope of asynchronous tests. When this configuration option is unset, it defaults to function scope. Possible values are: ``function``, ``class``, ``module``, ``package``, ``session``

.. _configuration/asyncio_debug:

asyncio_debug
=============
Enables `asyncio debug mode <https://docs.python.org/3/library/asyncio-dev.html#debug-mode>`_ for the default event loop used by asynchronous tests and fixtures.

The debug mode can be set by the ``asyncio_debug`` configuration option in the `configuration file
<https://docs.pytest.org/en/latest/reference/customize.html>`_:

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_debug = true

The value can also be set via the ``--asyncio-debug`` command-line option:

.. code-block:: bash

   $ pytest tests --asyncio-debug

By default, asyncio debug mode is disabled.

asyncio_mode
============
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

.. _configuration/asyncio_experimental_task_per_fixture:

asyncio_experimental_task_per_fixture
=====================================

Runs each async fixture in an asyncio task of its own, from setup to teardown, so that task groups and timeouts can span an async generator fixture's ``yield``.
See :ref:`concepts/tasks` for an explanation.

The option is experimental: its behavior may change in any release.
It requires Python 3.11 or later; enabling it on Python 3.10 is a usage error.
Defaults to ``false``.

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_experimental_task_per_fixture = true

.. _configuration/asyncio_experimental_task_per_fixture/cancellation:

Cancellation and cleanup
------------------------

A fixture can be cancelled while in use, for example when a background task in its task group fails or its timeout expires.
Then:

* The async test or fixture setup running on the fixture's event loop, if any, is cancelled.
* The fixture's own cleanup waits until pytest tears it down, after its dependents, in pytest's usual order.
  The cancellation is then raised at its ``yield``.
* Until then, new async tests and fixture setups on the fixture's event loop fail with an error that names the fixture.
  This affects the remaining async tests in the fixture's scope that run on that event loop.
  A function-scoped fixture affects no other test, because it is torn down right after its test.

When an exception interrupts the event loop, for example Ctrl-C or an exception raised by a signal handler, pytest-asyncio cancels the running async test or fixture and waits for its cleanup while the fixtures it uses are still available.
Without this option, only Ctrl-C is handled this way.

.. _configuration/asyncio_experimental_task_per_fixture/limitations:

Limitations
-----------

Cancelling a task that pytest-asyncio uses, for example by cancelling every task in ``asyncio.all_tasks()``, can fail a test or fixture, cut its cleanup short, or make code that then waits for that task hang.

If a fixture's AnyIO cancel scope is cancelled while the fixture is in use, the fixture uses extra CPU until pytest tears it down, for example while its dependents clean up.
