=======
Markers
=======

.. _reference/markers/asyncio:

``pytest.mark.asyncio``
=======================
A coroutine or async generator with this marker is treated as a test function by pytest.
The marked function is executed as an asyncio task in the event loop provided by pytest-asyncio.

.. include:: function_scoped_loop_strict_mode_example.py
    :code: python

Multiple async tests in a single class or module can be marked using |pytestmark|_.

.. include:: function_scoped_loop_pytestmark_strict_mode_example.py
    :code: python

The ``pytest.mark.asyncio`` marker can be omitted entirely in |auto mode|_ where the *asyncio* marker is added automatically to *async* test functions.

By default, each test runs in it's own asyncio event loop.
Multiple tests can share the same event loop by providing a *loop_scope* keyword argument to the *asyncio* mark.
The supported scopes are *function,* *class,* and *module,* *package,* and *session*.
The following code example provides a shared event loop for all tests in `TestClassScopedLoop`:

.. include:: class_scoped_loop_strict_mode_example.py
    :code: python

Similar to class-scoped event loops, a module-scoped loop is provided when setting mark's scope to *module:*

.. include:: module_scoped_loop_strict_mode_example.py
    :code: python

Subpackages do not share the loop with their parent package.

Tests marked with *session* scope share the same event loop, even if the tests exist in different packages.

.. |auto mode| replace:: *auto mode*
.. _auto mode: ../../concepts.html#auto-mode
.. |pytestmark| replace:: ``pytestmark``
.. _pytestmark: http://doc.pytest.org/en/latest/example/markers.html#marking-whole-classes-or-modules
