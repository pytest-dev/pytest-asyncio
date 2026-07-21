from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_event_loop_policy_fixture_in_conftest_raises_usage_error(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(
        dedent("""\
            import asyncio
            import pytest

            @pytest.fixture
            def event_loop_policy():
                return asyncio.DefaultEventLoopPolicy()
            """)
    )
    pytester.makepyfile(
        dedent("""\
            import pytest

            @pytest.mark.asyncio
            async def test_anything():
                pass
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.stderr.no_fnmatch_line("INTERNALERROR> *")
    result.assert_outcomes(passed=0, failed=0, errors=0)
    assert result.ret != 0
    result.stderr.fnmatch_lines('*"event_loop_policy" fixture was removed*')


def test_event_loop_policy_fixture_in_test_module_raises_usage_error(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import asyncio
            import pytest

            @pytest.fixture
            def event_loop_policy():
                return asyncio.DefaultEventLoopPolicy()

            @pytest.mark.asyncio
            async def test_anything():
                pass
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.stderr.no_fnmatch_line("INTERNALERROR> *")
    assert result.ret != 0
    result.stderr.fnmatch_lines('*"event_loop_policy" fixture was removed*')


def test_event_loop_policy_fixture_message_mentions_loop_factories_hook(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(
        dedent("""\
            import asyncio
            import pytest

            @pytest.fixture
            def event_loop_policy():
                return asyncio.DefaultEventLoopPolicy()
            """)
    )
    pytester.makepyfile(
        dedent("""\
            import pytest

            @pytest.mark.asyncio
            async def test_anything():
                pass
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.stderr.fnmatch_lines("*pytest_asyncio_loop_factories*")


def test_suite_without_event_loop_policy_fixture_runs_fine(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest

            @pytest.mark.asyncio
            async def test_anything():
                pass
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
