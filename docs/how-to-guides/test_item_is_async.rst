=======================================
How to tell if a test function is async
=======================================
Use ``pytest_asyncio.is_async_item`` to determine if a test item is asynchronous and managed by pytest-asyncio.

.. include:: test_item_is_async_example.py
    :code: python
