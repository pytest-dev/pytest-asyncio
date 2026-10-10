"""Custom task factories with asyncio_experimental_task_per_fixture."""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio_experimental_task_per_fixture requires Python 3.11",
)


def test_a_task_factory_that_fails_without_closing_the_coroutine_leaves_no_warning(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest_asyncio

        def reject_task(loop, coro, **kwargs):
            raise RuntimeError("task creation failed")

        @pytest_asyncio.fixture
        def loop():
            loop = asyncio.get_event_loop()
            loop.set_task_factory(reject_task)
            yield loop
            loop.set_task_factory(None)

        @pytest_asyncio.fixture
        async def value(loop):
            return 42

        def test_uses_value(value):
            pass
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*RuntimeError: task creation failed*"])
    assert "never awaited" not in result.stdout.str() + result.stderr.str()
