=======================================================
How to run all tests in a module in the same event loop
=======================================================
All tests can be run inside the same event loop by marking them with ``pytest.mark.asyncio(scope="module")``.
This is easily achieved by adding a `pytestmark` statement to your module.

.. include:: module_scoped_loop_example.py
    :code: python
