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

.. code-block:: python

    import asyncio

    import pytest

    # All test coroutines will be treated as marked.
    pytestmark = pytest.mark.asyncio


    async def test_example(event_loop):
        """No marker!"""
        await asyncio.sleep(0, loop=event_loop)

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

.. code-block:: python

    import asyncio

    import pytest


    @pytest.mark.asyncio_event_loop
    class TestClassScopedLoop:
        loop: asyncio.AbstractEventLoop

        @pytest.mark.asyncio
        async def test_remember_loop(self):
            TestClassScopedLoop.loop = asyncio.get_running_loop()

        @pytest.mark.asyncio
        async def test_this_runs_in_same_loop(self):
            assert asyncio.get_running_loop() is TestClassScopedLoop.loop

In *auto* mode, the ``pytest.mark.asyncio`` marker can be omitted:

.. code-block:: python

    import asyncio

    import pytest


    @pytest.mark.asyncio_event_loop
    class TestClassScopedLoop:
        loop: asyncio.AbstractEventLoop

        async def test_remember_loop(self):
            TestClassScopedLoop.loop = asyncio.get_running_loop()

        async def test_this_runs_in_same_loop(self):
            assert asyncio.get_running_loop() is TestClassScopedLoop.loop

Similarly, a module-scoped loop is provided when adding the `asyncio_event_loop` mark to the module:

.. code-block:: python

    import asyncio

    import pytest

    pytestmark = pytest.mark.asyncio_event_loop

    loop: asyncio.AbstractEventLoop


    async def test_remember_loop():
        global loop
        loop = asyncio.get_running_loop()


    async def test_this_runs_in_same_loop():
        global loop
        assert asyncio.get_running_loop() is loop


    class TestClassA:
        async def test_this_runs_in_same_loop(self):
            global loop
            assert asyncio.get_running_loop() is loop

The `asyncio_event_loop` mark supports an optional `policy` keyword argument to set the asyncio event loop policy.

.. code-block:: python

    import asyncio

    import pytest


    class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
        pass


    @pytest.mark.asyncio_event_loop(policy=CustomEventLoopPolicy())
    class TestUsesCustomEventLoopPolicy:
        @pytest.mark.asyncio
        async def test_uses_custom_event_loop_policy(self):
            assert isinstance(asyncio.get_event_loop_policy(), CustomEventLoopPolicy)


The ``policy`` keyword argument may also take an iterable of event loop policies. This causes tests under by the `asyncio_event_loop` mark to be parametrized with different policies:

.. code-block:: python

    import asyncio

    import pytest

    import pytest_asyncio


    @pytest.mark.asyncio_event_loop(
        policy=[
            asyncio.DefaultEventLoopPolicy(),
            uvloop.EventLoopPolicy(),
        ]
    )
    class TestWithDifferentLoopPolicies:
        @pytest.mark.asyncio
        async def test_parametrized_loop(self):
            pass


If no explicit policy is provided, the mark will use the loop policy returned by ``asyncio.get_event_loop_policy()``.

.. |pytestmark| replace:: ``pytestmark``
.. _pytestmark: http://doc.pytest.org/en/latest/example/markers.html#marking-whole-classes-or-modules
