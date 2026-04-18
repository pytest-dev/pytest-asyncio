======================================
How to test with different event loops
======================================

.. warning::

   Overriding the *event_loop_policy* fixture is deprecated and will be removed in a future version of pytest-asyncio. Use the ``pytest_asyncio_loop_factories`` hook instead. See :doc:`custom_loop_factory` for details.

Parametrizing the *event_loop_policy* fixture parametrizes all async tests. The following example causes all async tests to run multiple times, once for each event loop in the fixture parameters:

.. include:: multiple_loops_example.py
    :code: python

You may choose to limit the scope of the fixture to *package,* *module,* or *class,* if you only want a subset of your tests to run with different event loops.
