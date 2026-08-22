=======================
How to test with uvloop
=======================

Define a ``pytest_asyncio_loop_factories`` hook in your *conftest.py* that maps factory names to loop factories:

.. code-block:: python

    import uvloop


    def pytest_asyncio_loop_factories(config, item):
        return {
            "uvloop": uvloop.new_event_loop,
        }

.. seealso::

   :doc:`custom_loop_factory`
      More details on the ``pytest_asyncio_loop_factories`` hook, including per-test factory selection and multiple factory parametrization.
