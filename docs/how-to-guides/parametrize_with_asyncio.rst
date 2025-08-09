=====================================
How to parametrize asynchronous tests
=====================================

The ``pytest.mark.parametrize`` marker works with asynchronous tests the same as with synchronous tests. You can apply both ``pytest.mark.asyncio`` and ``pytest.mark.parametrize`` to asynchronous test functions:

.. include:: parametrize_with_asyncio_example.py
    :code: python

.. note::
   Whilst asynchronous tests can be parametrized, each individual test case still runs sequentially, not concurrently. For more information about how pytest-asyncio executes tests, see :ref:`concepts/concurrent_execution`.
