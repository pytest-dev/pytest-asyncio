from textwrap import dedent


def test_warn_asyncio_marker_for_regular_func(testdir):
    testdir.makepyfile(
        dedent(
            """\
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio
        def test_a():
            pass
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
            default
    """
        ),
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*is marked with '@pytest.mark.asyncio' but it is not an async function.*"]
    )
