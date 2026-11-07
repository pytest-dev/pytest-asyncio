===================================================
Applying the asyncio marker from a plugin
===================================================
Use the ``pytest_pycollect_makeitem`` hook to apply the ``asyncio`` marker to test functions collected by your plugin. This hook runs before pytest-asyncio specializes async test items and parametrizes them, so marked tests are handled like explicitly marked asyncio tests.

.. include:: apply_asyncio_marker_from_plugin_example.py
    :code: python

Marking tests in ``pytest_collection_modifyitems`` instead does not work: by the time that hook runs, pytest-asyncio has already specialized and parametrized the test items (for example for ``loop_scope`` and ``loop_factory``), so a marker added there will not turn the test into an asyncio test.
