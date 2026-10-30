"""Async fixtures whose setup or teardown is cancelled."""

from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_cancelled_teardown_does_not_prevent_teardown_of_other_fixtures(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        torn_down = []

        @pytest.fixture
        def sync_fixture():
            yield
            torn_down.append("sync_fixture")

        @pytest_asyncio.fixture
        async def cancelled_teardown():
            task = asyncio.create_task(asyncio.sleep(3600))
            yield
            task.cancel()
            await task

        @pytest.mark.asyncio
        async def test_requests_fixtures(sync_fixture, cancelled_teardown):
            pass

        def test_other_fixture_was_torn_down():
            assert torn_down == ["sync_fixture"]
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_requests_fixtures*",
            "E*CancelledError",
            "The above exception was the direct cause of the following exception:",
            "*PytestAsyncioError: The teardown of async fixture "
            "'cancelled_teardown' was cancelled.",
        ]
    )


@pytest.mark.parametrize("fixture_end", ("yield", "return"))
def test_cancelled_setup_of_module_scoped_fixture_is_setup_error_of_each_test(
    pytester: Pytester, fixture_end: str
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = module")
    pytester.makepyfile(dedent(f"""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="module")
        async def cancelled_setup():
            task = asyncio.create_task(asyncio.sleep(3600))
            task.cancel()
            await task
            {fixture_end}

        @pytest.mark.asyncio(loop_scope="module")
        async def test_first(cancelled_setup):
            pass

        @pytest.mark.asyncio(loop_scope="module")
        async def test_second(cancelled_setup):
            pass
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=2)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_first*",
            "*PytestAsyncioError: The setup of async fixture "
            "'cancelled_setup' was cancelled.",
            "*ERROR at setup of test_second*",
            "*PytestAsyncioError: The setup of async fixture "
            "'cancelled_setup' was cancelled.",
        ]
    )
