from textwrap import dedent


def test_task_canceled_on_test_end(testdir):
    testdir.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio
        async def test_a():
            loop = asyncio.get_event_loop()

            async def run_forever():
                while True:
                    await asyncio.sleep(0.1)

            loop.create_task(run_forever())
        """
        )
    )
    testdir.makefile(
        ".ini",
        pytest=dedent(
            """\
        [pytest]
        asyncio_mode = strict
        filterwarnings =
            error
    """
        ),
    )
    result = testdir.runpytest_subprocess()
    result.assert_outcomes(passed=1)
    result.stderr.no_fnmatch_line("Task was destroyed but it is pending!")
