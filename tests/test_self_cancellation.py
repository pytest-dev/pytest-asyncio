"""Async tests that cancel their own task."""

from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_a_test_that_cancels_itself_fails_and_its_fixture_is_torn_down_normally(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def resource():
            yield
            await asyncio.sleep(0)
            print("teardown finished")

        @pytest.mark.asyncio
        async def test_cancels_itself(resource):
            asyncio.current_task().cancel()
            await asyncio.sleep(0)
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "*_ test_cancels_itself _*",
            "*CancelledError*",
            "*Captured stdout teardown*",
            "teardown finished",
        ]
    )


def test_a_keyboard_interrupt_raised_after_the_test_cancels_itself_stops_the_session(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        @pytest.mark.asyncio
        async def test_cancels_itself():
            asyncio.current_task().cancel()
            raise KeyboardInterrupt
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes()
