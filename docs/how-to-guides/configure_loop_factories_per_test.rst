========================================================
How to configure event loop factories from the test item
========================================================

``pytest_asyncio_loop_factories`` is called with the current pytest ``item``.
Use that item to decide which named event loop factories are available for the test being collected.

For example, a hook can inspect the test's fixtures and return a different factory mapping for tests that request a particular fixture.
In ``conftest.py``, check the current item's fixture names and build the factory mapping for that item:

.. include:: configure_loop_factories_per_test/conftest.py
   :code: python

Then request the fixture from tests that should use the custom factory:

.. include:: configure_loop_factories_per_test/test_extra_loop_factories.py
   :code: python

In this example, ``test_runs_with_default_factory_only`` is parametrized only over ``default``, while ``test_runs_with_custom_factory_only`` is parametrized only over ``custom``.

The same pattern works with any information available from the current pytest item, such as fixture names, markers, node IDs, or file paths.

Because this is a standard pytest hook, its placement also matters.
An implementation in a nested ``conftest.py`` applies to tests collected under that directory.
Use this when a whole package or directory should share the same factory set.

For declaring factories without item-specific logic, see :doc:`custom_loop_factory`.

For selecting a subset of available factories from a test, see :doc:`run_test_with_specific_loop_factories`.
