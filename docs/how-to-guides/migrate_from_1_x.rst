.. _how_to_guides/migrate_from_1_x:

======================================
How to migrate from pytest-asyncio v1
======================================
1. If your test suite (or a plugin/conftest it uses) defines an *event_loop_policy* fixture, remove it. The fixture no longer has any effect; defining one now raises a usage error at collection time. Move the customization into a ``pytest_asyncio_loop_factories`` hook implementation instead. See :doc:`custom_loop_factory` and :doc:`uvloop`.
2. Change all occurrences of ``pytest.mark.asyncio(scope="…")`` to ``pytest.mark.asyncio(loop_scope="…")``. The deprecated *scope* keyword argument to the *asyncio* marker is no longer accepted at all.
3. Expect a new ``PytestAsyncioLoopScopeMismatchWarning`` to appear if a test or fixture (transitively) depends on an async fixture with a different effective *loop_scope*. This is new in v2 and can surface pre-existing bugs in test suites that already use *loop_scope*, sometimes in bulk, on first upgrade: a test and a fixture running on different event loops can silently break objects (such as ``asyncio.Future``, ``asyncio.Task``, or ``asyncio.Lock``) bound to the loop they were created on. See :doc:`../reference/warnings` for how to fix or, if the mismatch is intentional, silence individual instances.
4. If your code relies on the return type of ``pytest_asyncio.is_async_test``, note that it now returns a plain ``bool`` rather than a ``TypeIs`` type guard, since the check is no longer an ``isinstance`` check against a pytest-asyncio-specific ``Item`` subclass.
