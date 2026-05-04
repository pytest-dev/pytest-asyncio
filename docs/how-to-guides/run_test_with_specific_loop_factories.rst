=========================================================
How to run a test with specific event loop factories only
=========================================================

``pytest_asyncio_loop_factories`` determines which named event loop factories are available for each test item.
By default, pytest-asyncio parametrizes a test with every factory returned for that item.
Use ``loop_factories`` to select a subset of the factory names returned by the hook.

Assume ``conftest.py`` provides two named factories:

.. include:: run_test_with_specific_loop_factories/conftest.py
   :code: python

Then use ``loop_factories`` to select which available factory names a test should run with:

.. include:: run_test_with_specific_loop_factories/test_loop_factories_subset.py
   :code: python

If a requested factory name is not available from the hook, the test variant for that factory is skipped.

For declaring the factories themselves, see :doc:`custom_loop_factory`.

For choosing the available factories from the pytest item, see :doc:`configure_loop_factories_per_test`.
