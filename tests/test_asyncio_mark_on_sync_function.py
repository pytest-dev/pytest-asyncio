from textwrap import dedent

from pytest import Pytester


def test_warn_asyncio_marker_for_regular_func(pytester: Pytester):
    pytester.makepyfile(
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
    pytester.makefile(
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
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["*is marked with '@pytest.mark.asyncio' but it is not an async function.*"]
    )
