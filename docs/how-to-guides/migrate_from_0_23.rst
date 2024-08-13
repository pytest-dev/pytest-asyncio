========================================
How to migrate from pytest-asyncio v0.23
========================================
The following steps assume that your test suite has no re-implementations of the *event_loop* fixture, nor explicit fixtures requests for it. If this isn't the case, please follow the :ref:`migration guide for pytest-asyncio v0.21. <how_to_guides/migrate_from_0_21>`

1. Explicitly set the *loop_scope* of async fixtures by replacing occurrences of ``@pytest.fixture(scope="…")`` and ``@pytest_asyncio.fixture(scope="…")`` with ``@pytest_asyncio.fixture(loop_scope="…", scope="…")`` such that *loop_scope* and *scope* are the same. If you use auto mode, resolve all import errors from missing imports of *pytest_asyncio*. If your async fixtures all use the same *loop_scope*, you may choose to set the *asyncio_default_fixture_loop_scope* configuration option to that loop scope, instead.
2. If you haven't set *asyncio_default_fixture_loop_scope*, set it to *function* to address the deprecation warning about the unset configuration option.
3. Change all occurrences of ``pytest.mark.asyncio(scope="…")`` to ``pytest.mark.asyncio(loop_scope="…")`` to address the deprecation warning about the *scope* argument to the *asyncio* marker.
