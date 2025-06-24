from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_task_is_cancelled_when_abandoned_by_test(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        @pytest.mark.asyncio
        async def test_create_task():
            async def coroutine():
                try:
                    while True:
                        await asyncio.sleep(0)
                finally:
                    raise RuntimeError("The task should be cancelled at this point.")

            asyncio.create_task(coroutine())
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
