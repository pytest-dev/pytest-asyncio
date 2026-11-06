from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_unset_default_fixture_loop_scope_does_not_warn_without_async_fixtures(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_mode = strict")
    pytester.makepyfile(dedent("""\
        def test_sync():
            assert True
        """))

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line(
        '*The configuration option "asyncio_default_fixture_loop_scope" is unset*'
    )
    result.stderr.no_fnmatch_line(
        '*The configuration option "asyncio_default_fixture_loop_scope" is unset*'
    )


def test_unset_default_fixture_loop_scope_warns_for_async_fixture(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_mode = strict")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def fix():
            return 1

        @pytest.mark.asyncio
        async def test_async(fix):
            assert fix == 1
        """))

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ['*The configuration option "asyncio_default_fixture_loop_scope" is unset*']
    )
