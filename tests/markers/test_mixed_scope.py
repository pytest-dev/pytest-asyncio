from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_function_scoped_loop_restores_previous_loop_scope(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest


            module_loop: asyncio.AbstractEventLoop

            @pytest.mark.asyncio(loop_scope="module")
            async def test_remember_loop():
                global module_loop
                module_loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="function")
            async def test_with_function_scoped_loop():
                pass

            @pytest.mark.asyncio(loop_scope="module")
            async def test_runs_in_same_loop():
                global module_loop
                assert asyncio.get_running_loop() is module_loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)
