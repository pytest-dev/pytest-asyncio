.. _how_to_guides/migrate_from_0_21:

========================================
How to migrate from pytest-asyncio v0.21
========================================
1. If your test suite re-implements the *event_loop* fixture, make sure the fixture implementations don't do anything besides creating a new asyncio event loop, yielding it, and closing it.
2. Convert all synchronous test cases requesting the *event_loop* fixture to asynchronous test cases.
3. Convert all synchronous fixtures requesting the *event_loop* fixture to asynchronous fixtures.
4. Remove the *event_loop* argument from all asynchronous test cases in favor of ``event_loop = asyncio.get_running_loop()``.
5. Remove the *event_loop* argument from all asynchronous fixtures in favor of ``event_loop = asyncio.get_running_loop()``.

Go through all re-implemented *event_loop* fixtures in your test suite one by one, starting with the the fixture with the deepest nesting level and take note of the fixture scope:

1. For all tests and fixtures affected by the re-implemented *event_loop* fixture, configure the *loop_scope* for async tests and fixtures to match the *event_loop* fixture scope. This can be done for each test and fixture individually using either the ``pytest.mark.asyncio(loop_scope="…")`` marker for async tests or ``@pytest_asyncio.fixture(loop_scope="…")`` for async fixtures. Alternatively, you can set the default loop scope for fixtures using the :ref:`asyncio_default_fixture_loop_scope <configuration/asyncio_default_fixture_loop_scope>` configuration option. Snippets to mark all tests with the same *asyncio* marker, thus sharing the same loop scope, are present in the how-to section of the documentation. Depending on the homogeneity of your test suite, you may want a mixture of explicit decorators and default settings.
2. Remove the re-implemented *event_loop* fixture.

If you haven't set the *asyncio_default_fixture_loop_scope* configuration option, yet, set it to *function* to silence the deprecation warning.
