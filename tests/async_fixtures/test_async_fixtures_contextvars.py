"""
Regression test for https://github.com/pytest-dev/pytest-asyncio/issues/127:
contextvars were not properly maintained among fixtures and tests.
"""

from __future__ import annotations

from textwrap import dedent
from typing import Literal

import pytest
from pytest import Pytester

_prelude = dedent(
    """
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
"""
)


def test_var_from_sync_generator_propagates_to_async(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
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
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_async_generator_propagates_to_sync(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
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
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_async_fixture_propagates_to_sync(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
        @pytest_asyncio.fixture
        async def var_fixture():
            _context_var.set("value")
            # Rely on async fixture teardown to reset the context var.

        @pytest.fixture
        def check_var_fixture(var_fixture):
            assert _context_var.get() == "value"

        def test(check_var_fixture):
            assert _context_var.get() == "value"
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_generator_reset_before_previous_fixture_cleanup(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
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
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_from_fixture_reset_before_previous_fixture_cleanup(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
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
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_previous_value_restored_after_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
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
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_var_set_to_existing_value_ok(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        _prelude
        + dedent(
            """
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
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_no_isolation_against_context_changes_in_sync_tests(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """
            import pytest
            import pytest_asyncio
            from contextvars import ContextVar

            _context_var = ContextVar("my_var")

            def test_sync():
                _context_var.set("new_value")

            @pytest.mark.asyncio
            async def test_async():
                assert _context_var.get() == "new_value"
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize("loop_scope", ("function", "module"))
def test_isolation_against_context_changes_in_async_tests(
    pytester: Pytester, loop_scope: Literal["function", "module"]
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            f"""
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
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
