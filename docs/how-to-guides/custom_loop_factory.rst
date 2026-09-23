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

Synchronous tests are not parametrized by the hook unless their statically
resolved fixture closure contains a pytest-asyncio-managed fixture. This
includes fixtures requested through test arguments, ``usefixtures``, autouse
fixtures, and transitive fixture dependencies. Such a test runs once for each
configured loop factory, ensuring the managed fixture is created and torn down
on the corresponding event loop.

Direct test parameters shadow fixtures with the same name and therefore do not
trigger parametrization through those fixtures. Indirect parameters continue to
use their fixture definitions normally.

A managed fixture requested only dynamically through
``request.getfixturevalue()`` is not known during collection and does not
trigger loop factory parametrization for a synchronous test.

pytest-asyncio relies on the static fixture closure supplied by pytest and does
not perform additional fixture traversal. Dependencies introduced only by a
dynamic ``pytest_generate_tests`` rewrite, or hidden behind an overridden
same-name fixture definition that pytest does not include in that closure, do
not trigger parametrization.

To run a test with only some configured factories, see :doc:`run_test_with_specific_loop_factories`.
