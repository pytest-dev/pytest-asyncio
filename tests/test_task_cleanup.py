from __future__ import annotations

from textwrap import dedent

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
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_a_task_left_running_by_a_fixture_is_cancelled_when_its_loop_closes(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        from io import StringIO

        import pytest
        import pytest_asyncio

        @pytest.fixture(scope="session")
        def output():
            stream = StringIO()
            yield stream
            assert stream.closed

        async def run_forever(output):
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                output.close()

        @pytest_asyncio.fixture(scope="module", loop_scope="module")
        async def background(output):
            return asyncio.create_task(run_forever(output))

        @pytest.mark.asyncio(loop_scope="module")
        async def test_starts_the_task(background):
            await asyncio.sleep(0)

        @pytest.mark.asyncio(loop_scope="module")
        async def test_task_still_runs(background):
            assert not background.done()
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(passed=2)
    assert "Task was destroyed" not in result.stdout.str() + result.stderr.str()


def test_a_sync_fixture_cancelling_every_task_after_a_test_leaves_later_tests_working(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_default_fixture_loop_scope = module\n"
        "asyncio_default_test_loop_scope = module"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        @pytest.fixture(autouse=True)
        def cancel_leftover_tasks():
            yield
            loop = asyncio.get_event_loop()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        async def test_leaves_a_task():
            asyncio.get_running_loop().create_task(asyncio.sleep(100))

        async def test_after():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=auto", timeout=30)

    result.assert_outcomes(passed=2)
