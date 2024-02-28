==========================================================
How to run all tests in the session in the same event loop
==========================================================
All tests can be run inside the same event loop by marking them with ``pytest.mark.asyncio(scope="session")``.
The easiest way to mark all tests is via a ``pytest_collection_modifyitems`` hook in the ``conftest.py`` at the root folder of your test suite.

.. include:: session_scoped_loop_example.py
    :code: python

Note that this will also override *all* manually applied marks in *strict* mode.
