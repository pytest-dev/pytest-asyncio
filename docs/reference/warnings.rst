========
Warnings
========

PytestAsyncioLoopScopeMismatchWarning
======================================
Warns that a test or fixture requests an async fixture whose effective *loop_scope* differs from its own.

Every async test and every async fixture runs on an event loop determined by its effective *loop_scope* (its own explicit *loop_scope* argument, else the configured default, else its pytest caching scope). When a test or fixture (transitively) depends on an async fixture with a *different* effective *loop_scope*, the two run on different event loops. This can silently break objects -- such as ``asyncio.Future``, ``asyncio.Task``, or ``asyncio.Lock`` -- that are bound to the loop they were created on.

.. code-block:: python

    import pytest
    import pytest_asyncio


    @pytest_asyncio.fixture(loop_scope="module")
    async def async_fixture(): ...


    @pytest.mark.asyncio(loop_scope="function")
    async def test_uses_fixture_from_a_different_loop(async_fixture):
        # async_fixture ran on the module-scoped loop, but this test
        # runs on its own function-scoped loop: PytestAsyncioLoopScopeMismatchWarning
        ...

If the mismatch is intentional, silence the warning for a specific test with the standard *filterwarnings* marker:

.. code-block:: python

    @pytest.mark.asyncio(loop_scope="function")
    @pytest.mark.filterwarnings(
        "ignore::pytest_asyncio.PytestAsyncioLoopScopeMismatchWarning"
    )
    async def test_uses_fixture_from_a_different_loop(async_fixture): ...
