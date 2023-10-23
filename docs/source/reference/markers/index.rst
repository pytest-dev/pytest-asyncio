=======
Markers
=======

``pytest.mark.asyncio``
=======================
A coroutine or async generator with this marker will be treated as a test function by pytest. The marked function will be executed as an
asyncio task in the event loop provided by the ``event_loop`` fixture.

In order to make your test code a little more concise, the pytest |pytestmark|_
feature can be used to mark entire modules or classes with this marker.
Only test coroutines will be affected (by default, coroutines prefixed by
``test_``), so, for example, fixtures are safe to define.

.. include:: pytestmark_asyncio_strict_mode_example.py
    :code: python

In *auto* mode, the ``pytest.mark.asyncio`` marker can be omitted, the marker is added
automatically to *async* test functions.


``pytest.mark.asyncio_event_loop``
==================================
Test classes or modules with this mark provide a class-scoped or module-scoped asyncio event loop.

This functionality is orthogonal to the `asyncio` mark.
That means the presence of this mark does not imply that async test functions inside the class or module are collected by pytest-asyncio.
The collection happens automatically in `auto` mode.
However, if you're using strict mode, you still have to apply the `asyncio` mark to your async test functions.

The following code example uses the `asyncio_event_loop` mark to provide a shared event loop for all tests in `TestClassScopedLoop`:

.. include:: class_scoped_loop_strict_mode_example.py
    :code: python

In *auto* mode, the ``pytest.mark.asyncio`` marker can be omitted:

.. include:: class_scoped_loop_auto_mode_example.py
    :code: python

Similarly, a module-scoped loop is provided when adding the `asyncio_event_loop` mark to the module:

.. include:: module_scoped_loop_auto_mode_example.py
    :code: python

The `asyncio_event_loop` mark supports an optional `policy` keyword argument to set the asyncio event loop policy.

.. include:: class_scoped_loop_custom_policy_strict_mode_example.py
    :code: python


The ``policy`` keyword argument may also take an iterable of event loop policies. This causes tests under by the `asyncio_event_loop` mark to be parametrized with different policies:

.. include:: class_scoped_loop_custom_policies_strict_mode_example.py
    :code: python

If no explicit policy is provided, the mark will use the loop policy returned by ``asyncio.get_event_loop_policy()``.

Fixtures and tests sharing the same `asyncio_event_loop` mark are executed in the same event loop:

.. include:: class_scoped_loop_with_fixture_strict_mode_example.py
    :code: python

.. |pytestmark| replace:: ``pytestmark``
.. _pytestmark: http://doc.pytest.org/en/latest/example/markers.html#marking-whole-classes-or-modules
