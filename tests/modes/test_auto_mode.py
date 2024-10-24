from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_auto_mode_cmdline(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        async def test_a():
            await asyncio.sleep(0)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_auto_mode_cfg(pytester: Pytester):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_fixture_loop_scope = function
            asyncio_mode = auto
            """
        )
    )
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        async def test_a():
            await asyncio.sleep(0)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_auto_mode_async_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.fixture
        async def fixture_a():
            await asyncio.sleep(0)
            return 1

        async def test_a(fixture_a):
            await asyncio.sleep(0)
            assert fixture_a == 1
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_auto_mode_method_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'


        class TestA:

            @pytest.fixture
            async def fixture_a(self):
                await asyncio.sleep(0)
                return 1

            async def test_a(self, fixture_a):
                await asyncio.sleep(0)
                assert fixture_a == 1
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_auto_mode_static_method(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
        import asyncio

        pytest_plugins = 'pytest_asyncio'


        class TestA:

            @staticmethod
            async def test_a():
                await asyncio.sleep(0)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_auto_mode_static_method_fixture(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'


        class TestA:

            @staticmethod
            @pytest.fixture
            async def fixture_a():
                await asyncio.sleep(0)
                return 1

            @staticmethod
            async def test_a(fixture_a):
                await asyncio.sleep(0)
                assert fixture_a == 1
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)
