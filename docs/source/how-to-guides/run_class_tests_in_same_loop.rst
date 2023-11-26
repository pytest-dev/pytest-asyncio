======================================================
How to run all tests in a class in the same event loop
======================================================
All tests can be run inside the same event loop by marking them with ``pytest.mark.asyncio(scope="class")``.
This is easily achieved by using the *asyncio* marker as a class decorator.

.. include:: class_scoped_loop_example.py
    :code: python
