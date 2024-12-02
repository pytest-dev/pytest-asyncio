from __future__ import annotations

from textwrap import dedent

import pytest


def test_no_error_when_scope_passed_as_sole_keyword_argument(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio(loop_scope="session")
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*ValueError*")


def test_error_when_scope_passed_as_positional_argument(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio("session")
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio accepts only a keyword argument*"]
    )


def test_error_when_wrong_keyword_argument_is_passed(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio(cope="session")
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio accepts only a keyword argument 'loop_scope'*"]
    )


def test_error_when_additional_keyword_arguments_are_passed(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import pytest

            @pytest.mark.asyncio(loop_scope="session", more="stuff")
            async def test_anything():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio accepts only a keyword argument*"]
    )
