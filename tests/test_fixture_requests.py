"""Async fixtures and tests requested while an event loop runs."""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester


def test_an_async_fixture_requested_by_a_running_test_is_refused_without_harm(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="session", loop_scope="session")
        async def returned():
            return 42

        @pytest_asyncio.fixture(scope="session", loop_scope="session")
        async def yielded():
            yield 42

        @pytest.mark.asyncio
        async def test_requests_new_async_setups(request):
            with pytest.raises(RuntimeError, match="event loop is running"):
                request.getfixturevalue("returned")
            with pytest.raises(RuntimeError, match="event loop is running"):
                request.getfixturevalue("yielded")

        @pytest.mark.asyncio(loop_scope="session")
        async def test_session_loop_is_usable():
            pass
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(passed=2)
    # -W error turns an unawaited coroutine into a failed exit, after
    # the summary.
    assert result.ret == pytest.ExitCode.OK


def test_repeated_async_fixture_requests_report_the_original_setup_error(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="session", loop_scope="session")
        async def value():
            return 42

        @pytest.mark.asyncio
        async def test_repeated_request(request):
            with pytest.raises(RuntimeError, match="event loop is running") as first:
                request.getfixturevalue("value")
            with pytest.raises(RuntimeError, match="event loop is running") as second:
                request.getfixturevalue("value")
            assert second.value is first.value
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(passed=1)


def test_an_async_test_can_set_up_sync_fixtures_of_a_loop_not_yet_created(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="session", loop_scope="session")
        def returned():
            return 42

        @pytest_asyncio.fixture(scope="session", loop_scope="session")
        def yielded():
            yield 42

        @pytest.mark.asyncio
        async def test_requests_sync_fixtures(request):
            assert request.getfixturevalue("returned") == 42
            assert request.getfixturevalue("yielded") == 42

        @pytest.mark.asyncio(loop_scope="session")
        async def test_uses_the_fixtures_on_their_loop(returned, yielded):
            assert returned == yielded == 42
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(passed=2)


def test_async_tests_in_a_running_loop_report_setup_errors_without_coroutine_warnings(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(test_nested=dedent("""\
        import pytest

        @pytest.mark.asyncio
        async def test_async():
            pass
        """))
    launcher = pytester.makepyfile(run_pytest=dedent("""\
        import asyncio

        import pytest

        async def run():
            return pytest.main(
                ["test_nested.py", "--asyncio-mode=strict", "-W", "error"]
            )

        raise SystemExit(asyncio.run(run()))
        """))

    result = pytester.run(sys.executable, str(launcher), timeout=30)

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*RuntimeError: pytest-asyncio cannot start an async fixture or test "
            "while an event loop is running*"
        ]
    )
    output = result.stdout.str() + result.stderr.str()
    assert "never awaited" not in output
    assert "never retrieved" not in output
