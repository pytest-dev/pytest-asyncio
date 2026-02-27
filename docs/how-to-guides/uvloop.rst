=======================
How to test with uvloop
=======================

Redefining the *event_loop_policy* fixture will parametrize all async tests. The following example causes all async tests to run multiple times, once for each event loop in the fixture parameters:
Replace the default event loop policy in your *conftest.py:*

.. code-block:: python

    import asyncio

    import pytest
    import uvloop


    @pytest.fixture(scope="session")
    def event_loop_policy():
        policy = asyncio.get_event_loop_policy()
        policy.set_event_loop_class(uvloop.EventLoop)
        return policy

You may choose to limit the scope of the fixture to *package,* *module,* or *class,* if you only want a subset of your tests to run with uvloop.
