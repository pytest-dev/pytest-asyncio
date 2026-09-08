=====================================
How to parametrize asynchronous tests
=====================================

The ``pytest.mark.parametrize`` marker works with asynchronous tests the same as with synchronous tests. You can apply both ``pytest.mark.asyncio`` and ``pytest.mark.parametrize`` to asynchronous test functions:

.. include:: parametrize_with_asyncio_example.py
    :code: python

.. note::
   Whilst asynchronous tests can be parametrized, each individual test case still runs sequentially, not concurrently. For more information about how pytest-asyncio executes tests, see :ref:`concepts/concurrent_execution`.

Using custom event loop factories
=================================

In strict mode, apply ``pytest.mark.asyncio`` to the test function, its class, or its module when using :doc:`custom_loop_factory`.
Adding the marker only to individual ``pytest.param(..., marks=pytest.mark.asyncio)`` values does not trigger ``pytest_asyncio_loop_factories``.
This applies to parameter values passed to either ``pytest.mark.parametrize`` or ``pytest.fixture(params=...)``.
Loop factory parametrization happens before those parameter-specific markers are available on the test function.

For example, define two loop factories in ``conftest.py``:

.. include:: parametrize_with_loop_factories/conftest.py
   :code: python

Then mark the parametrized test function itself:

.. include:: parametrize_with_loop_factories/test_loop_factories.py
   :code: python

Running this example with ``pytest --asyncio-mode=strict`` produces four test cases: each of the two values runs once with each loop factory.

If parameter values select different async backends, such as asyncio and Trio, use separate test functions with the appropriate backend marker instead.
Common checks can live in a shared helper function.
Marking the whole mixed-backend test with ``pytest.mark.asyncio`` would also make pytest-asyncio handle the other backend's cases.
