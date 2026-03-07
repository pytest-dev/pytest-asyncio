=====
Hooks
=====

``pytest_asyncio_loop_factories``
=================================

This hook returns a mapping from factory name strings to event loop factory callables for the current test item.

By default, each pytest-asyncio test is run once per configured factory. Tests managed by other async plugins are unaffected. Synchronous tests are not parametrized. The configured loop scope still determines how long each event loop instance is kept alive.

Factories should be callables without required parameters and should return an ``asyncio.AbstractEventLoop`` instance. The effective hook result must be a non-empty mapping of non-empty string names to callables.

When multiple ``pytest_asyncio_loop_factories`` implementations are present, pytest-asyncio uses the first non-``None`` result in pytest's hook dispatch order.

When the hook is defined, async tests are parametrized via ``pytest.metafunc.parametrize``, and mapping keys are used as test IDs. For example, a test ``test_example`` with an event loop factory key ``foo`` will appear as ``test_example[foo]`` in test output.
