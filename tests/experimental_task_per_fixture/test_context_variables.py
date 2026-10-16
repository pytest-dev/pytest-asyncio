"""Context variables with asyncio_experimental_task_per_fixture."""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio_experimental_task_per_fixture requires Python 3.11",
)


def test_an_async_fixture_context_is_restored_in_sync_code_when_its_teardown_fails(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
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
