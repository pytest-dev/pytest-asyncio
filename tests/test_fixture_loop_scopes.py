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


def test_unset_default_fixture_loop_scope_warns_when_async_fixture_is_used(
    pytester: Pytester,
):
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def async_fixture():
            return 1

        @pytest.mark.asyncio
        async def test_uses_async_fixture(async_fixture):
            assert async_fixture == 1
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        [
            "*PytestDeprecationWarning: The configuration option "
            '"asyncio_default_fixture_loop_scope" is unset*'
        ]
    )


def test_unset_default_fixture_loop_scope_warns_only_once(
    pytester: Pytester,
):
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def async_fixture_one():
            return 1

        @pytest_asyncio.fixture
        async def async_fixture_two():
            return 2

        @pytest.mark.asyncio
        async def test_uses_async_fixtures(async_fixture_one, async_fixture_two):
            assert (async_fixture_one, async_fixture_two) == (1, 2)
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
    warning_lines = [
        line
        for line in result.stdout.lines
        if 'asyncio_default_fixture_loop_scope" is unset' in line
    ]
    assert len(warning_lines) == 1


def test_unset_default_fixture_loop_scope_does_not_warn_when_option_is_set(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def async_fixture():
            return 1

        @pytest.mark.asyncio
        async def test_uses_async_fixture(async_fixture):
            assert async_fixture == 1
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
    assert 'asyncio_default_fixture_loop_scope" is unset' not in result.stdout.str()


def test_unset_default_fixture_loop_scope_does_not_warn_without_async_fixtures(
    pytester: Pytester,
):
    # The option only affects asynchronous fixtures, so a session that never
    # sets one up (e.g. a nested pytest run picked up via another config file)
    # must not warn. See https://github.com/pytest-dev/pytest-asyncio/issues/1033
    pytester.makepyfile(dedent("""\
        import pytest

        @pytest.mark.asyncio
        async def test_async_test_without_fixtures():
            assert True

        def test_sync_test():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
    assert 'asyncio_default_fixture_loop_scope" is unset' not in result.stdout.str()


def test_unset_default_fixture_loop_scope_does_not_warn_with_explicit_loop_scope(
    pytester: Pytester,
):
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture(loop_scope="function")
        async def async_fixture():
            return 1

        @pytest.mark.asyncio
        async def test_uses_async_fixture(async_fixture):
            assert async_fixture == 1
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)
    assert 'asyncio_default_fixture_loop_scope" is unset' not in result.stdout.str()
