from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_task_is_cancelled_when_abandoned_by_test(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
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
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1, warnings=1)


def test_warns_about_task_left_pending_by_test(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        async def wait_forever():
            await asyncio.Event().wait()

        @pytest.mark.asyncio
        async def test_leaves_task_pending():
            asyncio.create_task(wait_forever())

        @pytest.mark.asyncio
        async def test_awaits_its_task():
            await asyncio.create_task(asyncio.sleep(0))
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=2, warnings=1)
    result.stdout.fnmatch_lines(
        [
            "*warnings summary*",
            "test_warns_about_task_left_pending_by_test.py::test_leaves_task_pending",
            "*RuntimeWarning: Tasks were still pending when the function-scoped "
            "event loop was closed*",
            "*<Task pending name=* coro=<wait_forever() running at *>*",
        ]
    )


@pytest.mark.parametrize("loop_scope", ("class", "module", "package", "session"))
def test_warns_about_pending_tasks_when_loop_scope_ends(
    pytester: Pytester, loop_scope: str
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        __init__="",
        test_pending_task=dedent(f"""\
            import asyncio
            import pytest

            pytestmark = pytest.mark.asyncio(loop_scope="{loop_scope}")

            async def wait_forever():
                await asyncio.Event().wait()

            class TestPendingTask:
                task = None

                async def test_starts_task(self):
                    TestPendingTask.task = asyncio.create_task(wait_forever())

                async def test_task_is_still_pending(self):
                    await asyncio.sleep(0)
                    assert not TestPendingTask.task.done()
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=2, warnings=1)
    result.stdout.fnmatch_lines(
        [
            f"*RuntimeWarning: Tasks were still pending when the {loop_scope}-scoped "
            "event loop was closed*",
            "*<Task pending name=* coro=<wait_forever() running at *>*",
        ]
    )


def test_pending_tasks_warning_can_be_turned_into_an_error(pytester: Pytester):
    pytester.makeini(dedent("""\
        [pytest]
        asyncio_default_fixture_loop_scope = function
        filterwarnings =
            default
            error:Tasks were still pending:RuntimeWarning
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        async def wait_forever():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                print("task was cancelled")
                raise

        @pytest.mark.asyncio
        async def test_leaves_task_pending():
            asyncio.create_task(wait_forever())
        """))
    result = pytester.runpytest("--asyncio-mode=strict", "-s")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*task was cancelled",
            "*ERROR at teardown of test_leaves_task_pending*",
            "*RuntimeWarning: Tasks were still pending when the function-scoped "
            "event loop was closed*",
        ]
    )
