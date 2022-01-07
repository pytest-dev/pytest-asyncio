from textwrap import dedent

pytest_plugins = "pytester"


def test_strict_mode_cmdline(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio
        async def test_a():
            await asyncio.sleep(0)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_strict_mode_cfg(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio
        async def test_a():
            await asyncio.sleep(0)
        """
        )
    )
    pytester.makefile(".ini", pytest="[pytest]\nasyncio_mode = strict\n")
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_strict_mode_method_fixture(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest
        import pytest_asyncio

        pytest_plugins = 'pytest_asyncio'

        class TestA:

            @pytest_asyncio.fixture
            async def fixture_a(self):
                await asyncio.sleep(0)
                return 1

            @pytest.mark.asyncio
            async def test_a(self, fixture_a):
                await asyncio.sleep(0)
                assert fixture_a == 1
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)
