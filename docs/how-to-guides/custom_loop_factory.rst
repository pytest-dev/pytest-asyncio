==================================================
How to use custom event loop factories for tests
==================================================

pytest-asyncio can run asynchronous tests with custom event loop factories by defining a ``pytest_asyncio_loop_factories`` hook in ``conftest.py``. The hook returns the factories to use for the current test item:

.. code-block:: python

   import asyncio

   import pytest


   class CustomEventLoop(asyncio.SelectorEventLoop):
       pass


   def pytest_asyncio_loop_factories(config, item):
       return [CustomEventLoop]

When multiple factories are returned, each asynchronous test is run once per factory. Synchronous tests are not parametrized. The configured loop scope still determines how long each event loop instance is kept alive.

Factories should be callables without required parameters and should return an ``asyncio.AbstractEventLoop`` instance. The hook must return a non-empty sequence for every asyncio test.

When multiple ``pytest_asyncio_loop_factories`` implementations are present, pytest-asyncio uses the first non -``None`` result in pytest's normal hook dispatch order.

To select different factories for specific tests, you can inspect ``item``:

.. code-block:: python

   import asyncio

   import uvloop


   def pytest_asyncio_loop_factories(config, item):
       if item.get_closest_marker("uvloop"):
           return [uvloop.new_event_loop]
       else:
           return [asyncio.new_event_loop]

Factory selection can vary per test item, regardless of loop scope. In other words, with ``module``/``package``/``session`` loop scopes you can still choose different factories for different tests by inspecting ``item``.

.. note::

   When the hook is defined, async tests are parametrized, so factory names are appended to test IDs. For example, a test ``test_example`` with factory ``CustomEventLoop`` will appear as ``test_example[CustomEventLoop]`` in the test output.
