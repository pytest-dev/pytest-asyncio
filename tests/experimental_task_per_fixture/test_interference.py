"""
Code that stops the event loop or cancels tasks that it did not create.

With asyncio_experimental_task_per_fixture, pytest-asyncio runs the loop
until its own tasks finish. Code that interferes with them fails the
test or fixture that runs it.
"""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio_experimental_task_per_fixture requires Python 3.11",
)


def test_an_async_fixture_cancelling_every_other_task_fails_its_teardown_with_a_hint(
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

        @pytest_asyncio.fixture(autouse=True)
        async def cancel_leftover_tasks():
            yield
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()

        async def test_leaves_a_task():
            asyncio.get_running_loop().create_task(asyncio.sleep(100))
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=auto", timeout=30)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_leaves_a_task*",
            "*Cancel only tasks that your code created*",
        ]
    )


def test_a_test_cancelling_every_other_task_fails_with_a_hint_and_later_tests_run(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        @pytest.mark.asyncio
        async def test_cancels_every_other_task():
            others = [
                task
                for task in asyncio.all_tasks()
                if task is not asyncio.current_task()
            ]
            for task in others:
                task.cancel()
            await asyncio.gather(*others, return_exceptions=True)

        @pytest.mark.asyncio
        async def test_next():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*_ test_cancels_every_other_task _*",
            "*Cancel only tasks that your code created*",
        ]
    )


def test_a_test_that_stops_the_loop_is_cancelled_before_its_fixtures_are_torn_down(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def report():
            with open("report.txt", "w") as stream:
                yield stream

        @pytest.mark.asyncio
        async def test_stops_the_loop(report):
            asyncio.get_running_loop().stop()
            await asyncio.sleep(0)
            report.write("ran after the loop stopped")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1)
    assert (pytester.path / "report.txt").read_text() == ""
