========================================================
How to run all tests in a package in the same event loop
========================================================
All tests can be run inside the same event loop by marking them with ``pytest.mark.asyncio(scope="package")``.
Add the following code to the ``__init__.py`` of the test package:

.. include:: package_scoped_loop_example.py
    :code: python

Note that this marker is not passed down to tests in subpackages.
Subpackages constitute their own, separate package.
