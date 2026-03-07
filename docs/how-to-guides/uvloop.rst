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

Using the event_loop_policy fixture
-----------------------------------

.. note::

   ``asyncio.AbstractEventLoopPolicy`` is deprecated as of Python 3.14 (removal planned for 3.16), and ``uvloop.EventLoopPolicy`` will be removed alongside it. Prefer the hook approach above.

For older versions of Python and uvloop, you can override the *event_loop_policy* fixture in your *conftest.py:*

.. code-block:: python

    import pytest
    import uvloop


    @pytest.fixture(scope="session")
    def event_loop_policy():
        return uvloop.EventLoopPolicy()

You may choose to limit the scope of the fixture to *package,* *module,* or *class,* if you only want a subset of your tests to run with uvloop.
