from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.parametrize(
    "fixture_scope", ("session", "package", "module", "class", "function")
)
def test_loop_scope_session_is_independent_of_fixture_scope(
    pytester: Pytester,
    fixture_scope: str,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent(f"""\
            import asyncio
            import pytest
            import pytest_asyncio

            loop: asyncio.AbstractEventLoop = None

            @pytest_asyncio.fixture(scope="{fixture_scope}", loop_scope="session")
            async def fixture():
                global loop
                loop = asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="session")
            async def test_runs_in_same_loop_as_fixture(fixture):
                global loop
                assert loop == asyncio.get_running_loop()
            """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("default_loop_scope", ("function", "module", "session"))
def test_default_loop_scope_config_option_changes_fixture_loop_scope(
    pytester: Pytester,
    default_loop_scope: str,
):
    pytester.makeini(dedent(f"""\
            [pytest]
            asyncio_default_fixture_loop_scope = {default_loop_scope}
            """))
    pytester.makepyfile(dedent(f"""\
            import asyncio
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture
            async def fixture_loop():
                return asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="{default_loop_scope}")
            async def test_runs_in_fixture_loop(fixture_loop):
                assert asyncio.get_running_loop() is fixture_loop
            """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_default_class_loop_scope_config_option_changes_fixture_loop_scope(
    pytester: Pytester,
):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = class
            """))
    pytester.makepyfile(dedent("""\
            import asyncio
            import pytest
            import pytest_asyncio

            class TestClass:
                @pytest_asyncio.fixture
                async def fixture_loop(self):
                    return asyncio.get_running_loop()

                @pytest.mark.asyncio(loop_scope="class")
                async def test_runs_in_fixture_loop(self, fixture_loop):
                    assert asyncio.get_running_loop() is fixture_loop
            """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_default_package_loop_scope_config_option_changes_fixture_loop_scope(
    pytester: Pytester,
):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = package
            """))
    pytester.makepyfile(
        __init__="",
        test_a=dedent("""\
            import asyncio
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture
            async def fixture_loop():
                return asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="package")
            async def test_runs_in_fixture_loop(fixture_loop):
                assert asyncio.get_running_loop() is fixture_loop
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_invalid_default_fixture_loop_scope_raises_error(pytester: Pytester):
    pytester.makeini("""\
        [pytest]
        asyncio_default_fixture_loop_scope = invalid_scope
        """)
    result = pytester.runpytest("--assert=plain")
    result.stderr.fnmatch_lines(
        [
            "ERROR: 'invalid_scope' is not a valid "
            "asyncio_default_fixture_loop_scope. Valid scopes are: "
            "function, class, module, package, session."
        ]
    )


def test_fixture_scope_default_runs_each_fixture_in_loop_of_its_own_scope(
    pytester: Pytester,
):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = fixture-scope
            asyncio_mode = auto
            """))
    pytester.makepyfile(dedent("""\
            import asyncio
            import pytest

            @pytest.fixture(scope="module")
            async def module_fixture_loop():
                return asyncio.get_running_loop()

            @pytest.fixture
            async def function_fixture_loop():
                return asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="module")
            async def test_module_fixture_runs_in_module_loop(module_fixture_loop):
                assert asyncio.get_running_loop() is module_fixture_loop

            async def test_function_fixture_runs_in_function_loop(
                function_fixture_loop,
            ):
                assert asyncio.get_running_loop() is function_fixture_loop
            """))
    result = pytester.runpytest()
    result.assert_outcomes(passed=2)


def test_explicit_loop_scope_overrides_fixture_scope_default(pytester: Pytester):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = fixture-scope
            """))
    pytester.makepyfile(dedent("""\
            import asyncio
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture(scope="module", loop_scope="session")
            async def fixture_loop():
                return asyncio.get_running_loop()

            @pytest.mark.asyncio(loop_scope="session")
            async def test_runs_in_fixture_loop(fixture_loop):
                assert asyncio.get_running_loop() is fixture_loop
            """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_fixture_scope_is_invalid_for_default_test_loop_scope(pytester: Pytester):
    pytester.makeini("""\
        [pytest]
        asyncio_default_fixture_loop_scope = function
        asyncio_default_test_loop_scope = fixture-scope
        """)
    result = pytester.runpytest("--assert=plain")
    result.stderr.fnmatch_lines(
        [
            "ERROR: 'fixture-scope' is not a valid "
            "asyncio_default_test_loop_scope. Valid scopes are: "
            "function, class, module, package, session."
        ]
    )


@pytest.mark.parametrize(
    ("mode", "test_decorator"),
    (
        ("strict", "@pytest.mark.asyncio(loop_scope='function')\n            "),
        ("auto", ""),
    ),
)
@pytest.mark.parametrize(
    "fixture_scope", ("function", "class", "module", "package", "session")
)
def test_warns_when_test_and_fixture_loop_scopes_differ(
    pytester: Pytester,
    mode: str,
    test_decorator: str,
    fixture_scope: str,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent(f"""\
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture(scope="{fixture_scope}", loop_scope="session")
            async def fixture():
                pass

            {test_decorator}async def test_mismatched_loop_scope(fixture):
                pass
            """))
    result = pytester.runpytest(f"--asyncio-mode={mode}", "-W", "default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        [
            "*PytestWarning: Async fixture 'fixture' with loop_scope='session' "
            "is requested by test 'test_mismatched_loop_scope' with "
            "loop_scope='function'.*"
        ]
    )


def test_warns_for_cached_fixture_regardless_of_test_order(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture(scope="session", loop_scope="session")
            async def fixture():
                pass

            @pytest.mark.asyncio(loop_scope="session")
            async def test_matching(fixture):
                pass

            @pytest.mark.skip(reason="skipped test should not warn")
            @pytest.mark.asyncio(loop_scope="function")
            async def test_skipped(fixture):
                pass

            @pytest.mark.asyncio(loop_scope="function")
            async def test_mismatched_first(fixture):
                pass

            @pytest.mark.asyncio(loop_scope="function")
            async def test_mismatched_second(fixture):
                pass
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=3, skipped=1, warnings=2)
    result.stdout.fnmatch_lines(
        [
            "*PytestWarning: Async fixture 'fixture' with loop_scope='session' "
            "is requested by test 'test_mismatched_first' with "
            "loop_scope='function'.*",
            "*PytestWarning: Async fixture 'fixture' with loop_scope='session' "
            "is requested by test 'test_mismatched_second' with "
            "loop_scope='function'.*",
        ]
    )
    result.stdout.no_fnmatch_line("*PytestWarning:*test_matching*")
    result.stdout.no_fnmatch_line("*PytestWarning:*test_skipped*")


@pytest.mark.parametrize(
    ("mode", "outer_decorator"),
    (
        ("strict", "pytest_asyncio.fixture(loop_scope='function')"),
        ("auto", "pytest.fixture"),
    ),
)
def test_warns_when_async_fixtures_have_different_loop_scopes(
    pytester: Pytester,
    mode: str,
    outer_decorator: str,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent(f"""\
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture(scope="session", loop_scope="session")
            async def inner_fixture():
                pass

            @{outer_decorator}
            async def outer_fixture(inner_fixture):
                pass

            @pytest.mark.asyncio(loop_scope="session")
            async def test_caches_inner(inner_fixture):
                pass

            @pytest.mark.asyncio(loop_scope="function")
            async def test_uses_outer(outer_fixture):
                pass
            """))
    result = pytester.runpytest(f"--asyncio-mode={mode}", "-W", "default")
    result.assert_outcomes(passed=2, warnings=1)
    result.stdout.fnmatch_lines(
        [
            "*PytestWarning: Async fixture 'inner_fixture' with "
            "loop_scope='session' is requested by fixture 'outer_fixture' with "
            "loop_scope='function'.*"
        ]
    )


def test_warns_when_mismatched_fixture_is_requested_via_sync_fixture(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest
            import pytest_asyncio

            @pytest_asyncio.fixture(loop_scope="session")
            async def async_fixture():
                pass

            @pytest.fixture
            def sync_fixture(async_fixture):
                return async_fixture

            @pytest.mark.asyncio(loop_scope="function")
            async def test_via_sync_fixture(sync_fixture):
                pass
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1, warnings=1)
    result.stdout.fnmatch_lines(
        [
            "*PytestWarning: Async fixture 'async_fixture' with "
            "loop_scope='session' is requested by test 'test_via_sync_fixture' "
            "with loop_scope='function'.*"
        ]
    )


def test_sync_test_requesting_async_fixture_does_not_warn(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
            import pytest_asyncio

            @pytest_asyncio.fixture(loop_scope="session")
            async def async_fixture():
                pass

            def test_sync(async_fixture):
                pass
            """))
    result = pytester.runpytest("--asyncio-mode=strict", "-W", "default")
    result.assert_outcomes(passed=1, warnings=0)
