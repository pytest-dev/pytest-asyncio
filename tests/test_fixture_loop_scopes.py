from __future__ import annotations

import warnings
from textwrap import dedent

import pytest
from pytest import PytestDeprecationWarning, Pytester


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
            "function, class, module, package, session, scope."
        ]
    )


def test_scope_default_runs_each_fixture_in_loop_of_its_own_scope(
    pytester: Pytester,
):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = scope
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


def test_explicit_loop_scope_overrides_scope_default(pytester: Pytester):
    pytester.makeini(dedent("""\
            [pytest]
            asyncio_default_fixture_loop_scope = scope
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


def test_scope_default_does_not_emit_deprecation_warning(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = scope")
    with warnings.catch_warnings():
        warnings.simplefilter("error", PytestDeprecationWarning)
        pytester.parseconfigure()


def test_scope_is_invalid_for_default_test_loop_scope(pytester: Pytester):
    pytester.makeini("""\
        [pytest]
        asyncio_default_fixture_loop_scope = function
        asyncio_default_test_loop_scope = scope
        """)
    result = pytester.runpytest("--assert=plain")
    result.stderr.fnmatch_lines(
        [
            "ERROR: 'scope' is not a valid "
            "asyncio_default_test_loop_scope. Valid scopes are: "
            "function, class, module, package, session."
        ]
    )
