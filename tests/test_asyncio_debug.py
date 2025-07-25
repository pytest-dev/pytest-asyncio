from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_asyncio_debug_disabled_by_default(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_debug_mode_disabled():
                loop = asyncio.get_running_loop()
                assert not loop.get_debug()
            """
        )
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_asyncio_debug_enabled_via_cli_option(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_debug_mode_enabled():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
            """
        )
    )
    result = pytester.runpytest("--asyncio-debug")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("config_value", ("true", "1"))
def test_asyncio_debug_enabled_via_config_option(pytester: Pytester, config_value: str):
    pytester.makeini(
        dedent(
            f"""\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_debug = {config_value}
            """
        )
    )
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_debug_mode_enabled():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
            """
        )
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("config_value", ("false", "0"))
def test_asyncio_debug_disabled_via_config_option(
    pytester: Pytester,
    config_value: str,
):
    pytester.makeini(
        dedent(
            f"""\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_debug = {config_value}
            """
        )
    )
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_debug_mode_disabled():
                loop = asyncio.get_running_loop()
                assert not loop.get_debug()
            """
        )
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_asyncio_debug_cli_option_overrides_config(pytester: Pytester):
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\nasyncio_debug = false"
    )
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_debug_mode_enabled():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
            """
        )
    )
    result = pytester.runpytest("--asyncio-debug")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("loop_scope", ("function", "module", "session"))
def test_asyncio_debug_with_different_loop_scopes(pytester: Pytester, loop_scope: str):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio(loop_scope="{loop_scope}")
            async def test_debug_mode_with_scope():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
            """
        )
    )
    result = pytester.runpytest("--asyncio-debug")
    result.assert_outcomes(passed=1)


def test_asyncio_debug_with_async_fixtures(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            @pytest_asyncio.fixture
            async def async_fixture():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
                return "fixture_value"

            @pytest.mark.asyncio
            async def test_debug_mode_with_fixture(async_fixture):
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
                assert async_fixture == "fixture_value"
            """
        )
    )
    result = pytester.runpytest("--asyncio-debug")
    result.assert_outcomes(passed=1)


def test_asyncio_debug_multiple_test_functions(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_debug_first():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()

            @pytest.mark.asyncio
            async def test_debug_second():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()

            @pytest.mark.asyncio
            async def test_debug_third():
                loop = asyncio.get_running_loop()
                assert loop.get_debug()
            """
        )
    )
    result = pytester.runpytest("--asyncio-debug")
    result.assert_outcomes(passed=3)
