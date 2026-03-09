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

By default, each asynchronous test is run once per configured factory. Synchronous tests are not parametrized. The configured loop scope still determines how long each event loop instance is kept alive.

Factories should be callables without required parameters and should return an ``asyncio.AbstractEventLoop`` instance. The effective hook result must be a non-empty mapping of non-empty string names to callables.

To run a test with only a subset of configured factories, use the ``loop_factories`` argument of ``pytest.mark.asyncio``:

.. code-block:: python

   import pytest


   @pytest.mark.asyncio(loop_factories=["custom"])
   async def test_only_with_custom_event_loop():
       pass


If ``loop_factories`` contains unknown names, pytest-asyncio raises a ``pytest.UsageError`` during collection.

When multiple ``pytest_asyncio_loop_factories`` implementations are present, pytest-asyncio uses the first non-``None`` result in pytest's hook dispatch order.

.. note::

   When the hook is defined, async tests are parametrized via ``pytest.metafunc.parametrize``, and mapping keys are used as test IDs. For example, a test ``test_example`` with an event loop factory key ``foo`` will appear as ``test_example[foo]`` in test output.
