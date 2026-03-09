from __future__ import annotations

from textwrap import dedent

import pytest


def test_no_error_when_scope_passed_as_sole_keyword_argument(
    pytester: pytest.Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            @pytest.mark.asyncio(loop_scope="session")
            async def test_anything():
                pass
            """))
    result = pytester.runpytest("--assert=plain")
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*ValueError*")


def test_error_when_scope_passed_as_positional_argument(
    pytester: pytest.Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            @pytest.mark.asyncio("session")
            async def test_anything():
                pass
            """))
    result = pytester.runpytest("--assert=plain")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio accepts only keyword arguments*"]
    )


def test_error_when_wrong_keyword_argument_is_passed(
    pytester: pytest.Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            @pytest.mark.asyncio(cope="session")
            async def test_anything():
                pass
            """))
    result = pytester.runpytest("--assert=plain")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio accepts only keyword arguments*"]
    )


def test_error_when_additional_keyword_arguments_are_passed(
    pytester: pytest.Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest

            @pytest.mark.asyncio(loop_scope="session", more="stuff")
            async def test_anything():
                pass
            """))
    result = pytester.runpytest("--assert=plain")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio accepts only keyword arguments*"]
    )


@pytest.mark.parametrize(
    "loop_factories_value",
    ('"custom"', "[]", '[""]', "[1]"),
)
def test_error_when_loop_factories_marker_value_is_invalid(
    pytester: pytest.Pytester, loop_factories_value: str
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
            import asyncio

            class CustomEventLoop(asyncio.SelectorEventLoop):
                pass

            def pytest_asyncio_loop_factories(config, item):
                return {"custom": CustomEventLoop}
            """))
    pytester.makepyfile(dedent(f"""\
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio(loop_factories={loop_factories_value})
            async def test_anything():
                pass
            """))
    result = pytester.runpytest("--assert=plain")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: mark.asyncio 'loop_factories' must be a non-empty sequence*"]
    )
