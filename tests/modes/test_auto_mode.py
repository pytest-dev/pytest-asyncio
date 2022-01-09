from textwrap import dedent

pytest_plugins = "pytester"


def test_auto_mode_cmdline(pytester):
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


def test_auto_mode_cfg(pytester):
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
    pytester.makefile(".ini", pytest="[pytest]\nasyncio_mode = auto\n")
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_auto_mode_async_fixture(pytester):
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


def test_auto_mode_method_fixture(pytester):
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
