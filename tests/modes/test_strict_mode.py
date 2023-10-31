from textwrap import dedent


def test_strict_mode_cmdline(testdir):
    testdir.makepyfile(
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
    result = testdir.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_strict_mode_cfg(testdir):
    testdir.makepyfile(
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
    testdir.makefile(".ini", pytest="[pytest]\nasyncio_mode = strict\n")
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_strict_mode_method_fixture(testdir):
    testdir.makepyfile(
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
    result = testdir.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_strict_mode_ignores_unmarked_coroutine(testdir):
    testdir.makepyfile(
        dedent(
            """\
        import pytest

        async def test_anything():
            pass
        """
        )
    )
    result = testdir.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(skipped=1, warnings=1)
    result.stdout.fnmatch_lines(["*async def functions are not natively supported*"])


def test_strict_mode_ignores_unmarked_fixture(testdir):
    testdir.makepyfile(
        dedent(
            """\
        import pytest

        # Not using pytest_asyncio.fixture
        @pytest.fixture()
        async def any_fixture():
            raise RuntimeError()

        async def test_anything(any_fixture):
            pass
        """
        )
    )
    result = testdir.runpytest("--asyncio-mode=strict", "-W default")
    result.assert_outcomes(skipped=1, warnings=2)
    result.stdout.fnmatch_lines(
        [
            "*async def functions are not natively supported*",
            "*coroutine 'any_fixture' was never awaited*",
        ],
    )
