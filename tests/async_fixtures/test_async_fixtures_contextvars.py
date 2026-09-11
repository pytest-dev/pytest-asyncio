"""
Regression test for https://github.com/pytest-dev/pytest-asyncio/issues/127:
contextvars were not properly maintained among fixtures and tests.
"""

from __future__ import annotations

import sys
from textwrap import dedent
from typing import Literal

import pytest
from pytest import Pytester

_prelude = dedent("""
    import pytest
    import pytest_asyncio
    from contextlib import contextmanager
    from contextvars import ContextVar

    _context_var = ContextVar("context_var")

    @contextmanager
    def context_var_manager(value):
        token = _context_var.set(value)
        try:
            yield
        finally:
            _context_var.reset(token)
""")


def test_var_from_sync_generator_propagates_to_async(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest.fixture
        def var_fixture():
            with context_var_manager("value"):
                yield

        @pytest_asyncio.fixture
        async def check_var_fixture(var_fixture):
            assert _context_var.get() == "value"

        @pytest.mark.asyncio
        async def test(check_var_fixture):
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_async_generator_propagates_to_sync(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest_asyncio.fixture
        async def var_fixture():
            with context_var_manager("value"):
                yield

        @pytest.fixture
        def check_var_fixture(var_fixture):
            assert _context_var.get() == "value"

        @pytest.mark.asyncio
        async def test(check_var_fixture):
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_async_fixture_propagates_to_sync(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest_asyncio.fixture
        async def var_fixture():
            _context_var.set("value")
            # Rely on async fixture teardown to reset the context var.

        @pytest.fixture
        def check_var_fixture(var_fixture):
            assert _context_var.get() == "value"

        def test(check_var_fixture):
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_generator_reset_before_previous_fixture_cleanup(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest_asyncio.fixture
        async def no_var_fixture():
            with pytest.raises(LookupError):
                _context_var.get()
            yield
            with pytest.raises(LookupError):
                _context_var.get()

        @pytest_asyncio.fixture
        async def var_fixture(no_var_fixture):
            with context_var_manager("value"):
                yield

        @pytest.mark.asyncio
        async def test(var_fixture):
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_fixture_reset_before_previous_fixture_cleanup(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest_asyncio.fixture
        async def no_var_fixture():
            with pytest.raises(LookupError):
                _context_var.get()
            yield
            with pytest.raises(LookupError):
                _context_var.get()

        @pytest_asyncio.fixture
        async def var_fixture(no_var_fixture):
            _context_var.set("value")
            # Rely on async fixture teardown to reset the context var.

        @pytest.mark.asyncio
        async def test(var_fixture):
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_previous_value_restored_after_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest_asyncio.fixture
        async def var_fixture_1():
            with context_var_manager("value1"):
                yield
                assert _context_var.get() == "value1"

        @pytest_asyncio.fixture
        async def var_fixture_2(var_fixture_1):
            with context_var_manager("value2"):
                yield
                assert _context_var.get() == "value2"

        @pytest.mark.asyncio
        async def test(var_fixture_2):
            assert _context_var.get() == "value2"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_set_to_existing_value_ok(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(_prelude + dedent("""
        @pytest_asyncio.fixture
        async def var_fixture():
            with context_var_manager("value"):
                yield

        @pytest_asyncio.fixture
        async def same_var_fixture(var_fixture):
            with context_var_manager(_context_var.get()):
                yield

        @pytest.mark.asyncio
        async def test(same_var_fixture):
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_no_isolation_against_context_changes_in_sync_tests(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
            import pytest
            import pytest_asyncio
            from contextvars import ContextVar

            _context_var = ContextVar("my_var")

            def test_sync():
                _context_var.set("new_value")

            @pytest.mark.asyncio
            async def test_async():
                assert _context_var.get() == "new_value"
            """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize("loop_scope", ("function", "module"))
def test_isolation_against_context_changes_in_async_tests(
    pytester: Pytester, loop_scope: Literal["function", "module"]
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent(f"""
            import pytest
            import pytest_asyncio
            from contextvars import ContextVar

            _context_var = ContextVar("my_var")

            @pytest.mark.asyncio(loop_scope="{loop_scope}")
            async def test_async_first():
                _context_var.set("new_value")

            @pytest.mark.asyncio(loop_scope="{loop_scope}")
            async def test_async_second():
                with pytest.raises(LookupError):
                    _context_var.get()
            """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_a_sync_fixture_assignment_is_seen_by_async_tests_on_new_and_reused_loops(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        from contextvars import ContextVar

        import pytest

        _context_var = ContextVar("context_var")

        @pytest.fixture
        def var_fixture():
            token = _context_var.set("value")
            yield
            _context_var.reset(token)

        @pytest.mark.asyncio(loop_scope="module")
        async def test_fixture_before_loop(var_fixture):
            assert _context_var.get() == "value"

        @pytest.mark.asyncio(loop_scope="module")
        async def test_fixture_after_loop(var_fixture):
            assert _context_var.get() == "value"

        @pytest.mark.asyncio(loop_scope="module")
        async def test_var_reset():
            with pytest.raises(LookupError):
                _context_var.get()
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


def test_a_sync_test_assignment_is_seen_by_later_async_tests_on_a_reused_loop(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        from contextvars import ContextVar

        import pytest

        _context_var = ContextVar("context_var")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_async_before():
            pass

        def test_sync():
            _context_var.set("value")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_async_after():
            assert _context_var.get() == "value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


def test_a_test_assignment_does_not_change_its_fixtures_teardown_context(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        from contextvars import ContextVar

        import pytest
        import pytest_asyncio

        _context_var = ContextVar("context_var")

        @pytest_asyncio.fixture
        async def var_fixture():
            _context_var.set("value")
            yield
            assert _context_var.get() == "value"

        @pytest.mark.asyncio
        async def test(var_fixture):
            _context_var.set("other")
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_an_async_test_assignment_is_not_seen_by_a_fixture_set_up_later(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        from contextvars import ContextVar

        import pytest
        import pytest_asyncio

        _context_var = ContextVar("context_var")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_set_var():
            _context_var.set("test value")

        @pytest_asyncio.fixture(loop_scope="module")
        async def var_fixture():
            with pytest.raises(LookupError):
                _context_var.get()
            yield

        @pytest.mark.asyncio(loop_scope="module")
        async def test_uses_var(var_fixture):
            pass
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_an_async_coroutine_fixture_assignment_is_undone_after_its_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        from contextvars import ContextVar

        import pytest
        import pytest_asyncio

        _context_var = ContextVar("context_var")

        @pytest_asyncio.fixture
        async def var_fixture():
            _context_var.set("value")

        def test_uses_var(var_fixture):
            assert _context_var.get() == "value"

        def test_after():
            with pytest.raises(LookupError):
                _context_var.get()
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_an_async_fixture_context_is_restored_in_sync_code_when_its_teardown_fails(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        from contextvars import ContextVar

        import pytest
        import pytest_asyncio

        _context_var = ContextVar("context_var")

        @pytest_asyncio.fixture
        async def var_fixture():
            _context_var.set("value")
            yield
            raise ValueError("teardown error")

        @pytest.mark.asyncio
        async def test_uses_var(var_fixture):
            pass

        def test_after():
            with pytest.raises(LookupError):
                _context_var.get()
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2, errors=1)
    result.stdout.fnmatch_lines(["*ValueError: teardown error*"])


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="Task.get_context() requires Python 3.12"
)
def test_the_current_task_context_is_the_context_of_the_fixture_or_test(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""
        import asyncio
        from contextvars import ContextVar

        import pytest
        import pytest_asyncio

        _context_var = ContextVar("context_var")

        @pytest_asyncio.fixture
        async def var_fixture():
            _context_var.set("fixture value")
            context = asyncio.current_task().get_context()
            assert context[_context_var] == "fixture value"
            yield
            context = asyncio.current_task().get_context()
            assert context[_context_var] == "fixture value"

        @pytest.mark.asyncio
        async def test(var_fixture):
            _context_var.set("test value")
            context = asyncio.current_task().get_context()
            assert context[_context_var] == "test value"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="loop.create_task() passes task factories a context from Python 3.11",
)
@pytest.mark.parametrize(
    ("task_per_fixture", "seen_by_sync_dependent"),
    [
        pytest.param("false", "missing", id="default runner"),
        pytest.param("true", "set by the task factory", id="experimental runner"),
    ],
)
def test_a_task_factory_assignment_in_the_task_context_reaches_sync_dependents(
    pytester: Pytester, task_per_fixture: str, seen_by_sync_dependent: str
):
    """Only the experimental runner passes this context to sync code."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""
        import asyncio
        import contextvars

        import pytest

        trace = contextvars.ContextVar("trace")

        def traced_task_factory(loop, coro, *, context=None, **kwargs):
            if context is None:
                context = contextvars.copy_context()
            context = context.copy()
            context.run(trace.set, "set by the task factory")
            return asyncio.Task(coro, loop=loop, context=context, **kwargs)

        def traced_loop_factory():
            loop = asyncio.new_event_loop()
            loop.set_task_factory(traced_task_factory)
            return loop

        def pytest_asyncio_loop_factories(config, item):
            return {"traced": traced_loop_factory}

        @pytest.fixture
        def trace_var():
            return trace
        """))
    pytester.makepyfile(dedent(f"""
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def traced_fixture(trace_var):
            assert trace_var.get() == "set by the task factory"

        @pytest.fixture
        def sync_dependent(traced_fixture, trace_var):
            assert trace_var.get("missing") == "{seen_by_sync_dependent}"

        @pytest.mark.asyncio
        async def test_uses_sync_dependent(sync_dependent):
            pass
        """))
    result = pytester.runpytest(
        "--asyncio-mode=strict",
        "-o",
        f"asyncio_experimental_task_per_fixture={task_per_fixture}",
    )
    result.assert_outcomes(passed=1)
