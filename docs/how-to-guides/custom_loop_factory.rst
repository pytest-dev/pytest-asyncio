================================================
How to use custom event loop factories for tests
================================================

pytest-asyncio can run asynchronous tests with custom event loop factories by implementing ``pytest_asyncio_loop_factories`` in ``conftest.py``. The hook provides the named event loop factories that are available for a test item by returning a mapping from factory names to loop factory callables:

.. code-block:: python

   import asyncio

   import pytest


   class CustomEventLoop(asyncio.SelectorEventLoop):
       pass


   def pytest_asyncio_loop_factories(config, item):
       return {
           "stdlib": asyncio.new_event_loop,
           "custom": CustomEventLoop,
       }

The hook receives the current pytest ``item``, so it can return different factory mappings for different tests. See :doc:`configure_loop_factories_per_test` for item-based factory configuration.

To run a test with only some configured factories, see :doc:`run_test_with_specific_loop_factories`.
