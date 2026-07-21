from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_warns_when_fixture_loop_scope_is_wider_than_test(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture(loop_scope="module")
            async def wide_fixture():
                return 1

            @pytest.mark.asyncio(loop_scope="function")
            async def test_narrow(wide_fixture):
                assert wide_fixture == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        "*PytestAsyncioLoopScopeMismatchWarning*'function'*'wide_fixture'*'module'*"
    )


def test_warns_when_fixture_loop_scope_is_narrower_than_test(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture(loop_scope="function")
            async def narrow_fixture():
                return 1

            @pytest.mark.asyncio(loop_scope="session")
            async def test_wide(narrow_fixture):
                assert narrow_fixture == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        "*PytestAsyncioLoopScopeMismatchWarning*'session'*'narrow_fixture'*'function'*"
    )


def test_warns_for_mismatch_reachable_only_transitively(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture(loop_scope="module")
            async def async_fixture():
                return 1

            @pytest.fixture
            def sync_fixture(async_fixture):
                return async_fixture

            @pytest.mark.asyncio(loop_scope="function")
            async def test_uses_sync_fixture(sync_fixture):
                assert sync_fixture == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        "*PytestAsyncioLoopScopeMismatchWarning*'async_fixture'*"
    )


def test_diamond_shaped_dependency_warns_only_once(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture(loop_scope="module")
            async def shared_fixture():
                return 1

            @pytest.fixture
            def fixture_a(shared_fixture):
                return shared_fixture

            @pytest.fixture
            def fixture_b(shared_fixture):
                return shared_fixture

            @pytest.mark.asyncio(loop_scope="function")
            async def test_uses_both(fixture_a, fixture_b):
                assert fixture_a == fixture_b == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    warning_lines = [
        line
        for line in result.stdout.lines
        if "PytestAsyncioLoopScopeMismatchWarning" in line and "shared_fixture" in line
    ]
    assert len(warning_lines) == 1


def test_no_warning_when_loop_scope_matches_despite_differing_cache_scope(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture(scope="module", loop_scope="session")
            async def fixture_with_matching_loop_scope():
                return 1

            @pytest.mark.asyncio(loop_scope="session")
            async def test_matches(fixture_with_matching_loop_scope):
                assert fixture_with_matching_loop_scope == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*PytestAsyncioLoopScopeMismatchWarning*")


def test_no_warning_for_sync_fixture_with_differing_cache_scope(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.fixture(scope="module")
            def plain_sync_fixture():
                return 1

            @pytest.mark.asyncio(loop_scope="function")
            async def test_uses_plain_sync_fixture(plain_sync_fixture):
                assert plain_sync_fixture == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*PytestAsyncioLoopScopeMismatchWarning*")


def test_mismatch_warning_can_be_silenced_via_filterwarnings_marker(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent("""\
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture(loop_scope="module")
            async def wide_fixture():
                return 1

            @pytest.mark.asyncio(loop_scope="function")
            @pytest.mark.filterwarnings(
                "ignore::pytest_asyncio.PytestAsyncioLoopScopeMismatchWarning"
            )
            async def test_narrow(wide_fixture):
                assert wide_fixture == 1
            """)
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*PytestAsyncioLoopScopeMismatchWarning*")
