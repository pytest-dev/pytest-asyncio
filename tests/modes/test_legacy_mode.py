from textwrap import dedent
import re

pytest_plugins = "pytester"


LEGACY_MODE = (
    "The 'asyncio_mode' default value will change to 'strict' in future, "
    "please explicitly use 'asyncio_mode=strict' or 'asyncio_mode=auto' "
    "in pytest configuration file."
)

LEGACY_ASYNCIO_FIXTURE = (
    "'@pytest.fixture' is applied to {name} "
    "in 'legacy' mode, "
    "please replace it with '@pytest_asyncio.pytest_asyncio' as a preparation "
    "for switching to 'strict' mode (or use 'auto' mode to seamlessly handle "
    "all these fixtures as asyncio-driven)."
).format(name="*")


def test_warning_for_legacy_mode_cmdline(pytester):
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
    result = pytester.runpytest("--asyncio-mode=legacy")
    assert result.parseoutcomes()["warnings"] == 1
    result.stdout.fnmatch_lines(["*" + LEGACY_MODE + "*"])


def test_warning_for_legacy_mode_cfg(pytester):
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
    pytester.makefile(".ini", pytest="[pytest]\nasyncio_mode = legacy\n")
    result = pytester.runpytest()
    assert result.parseoutcomes()["warnings"] == 1
    result.stdout.fnmatch_lines(["*" + LEGACY_MODE + "*"])
    result.stdout.no_fnmatch_line("*" + LEGACY_ASYNCIO_FIXTURE + "*")


def test_warning_for_legacy_fixture(pytester):
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

        @pytest.mark.asyncio
        async def test_a(fixture_a):
            await asyncio.sleep(0)
            assert fixture_a == 1
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=legacy")
    assert result.parseoutcomes()["warnings"] == 2
    result.stdout.fnmatch_lines(["*" + LEGACY_ASYNCIO_FIXTURE + "*"])


def test_warning_for_legacy_method_fixture(pytester):
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

            @pytest.mark.asyncio
            async def test_a(self, fixture_a):
                await asyncio.sleep(0)
                assert fixture_a == 1
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=legacy")
    assert result.parseoutcomes()["warnings"] == 2
    result.stdout.fnmatch_lines(["*" + LEGACY_ASYNCIO_FIXTURE + "*"])
