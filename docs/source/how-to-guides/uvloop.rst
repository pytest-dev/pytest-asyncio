=======================
How to test with uvloop
=======================

Replace the default event loop policy in your *conftest.py:*

.. code-block:: python

    import asyncio

    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
