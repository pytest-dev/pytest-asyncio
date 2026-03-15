================================================
How to use custom event loop factories for tests
================================================

pytest-asyncio can run asynchronous tests with custom event loop factories by implementing ``pytest_asyncio_loop_factories`` in ``conftest.py``. The hook returns a mapping from factory names to loop factory callables:

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

See :doc:`run_test_with_specific_loop_factories` for running tests with only a subset of configured factories.

See :doc:`../reference/hooks` and :doc:`../reference/markers/index` for the hook and marker reference.
