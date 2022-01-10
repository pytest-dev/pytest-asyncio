from textwrap import dedent

pytest_plugins = "pytester"


def test_timeout_ok(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio(timeout=0.01)
        @pytest.mark.xfail(strict=True, raises=asyncio.TimeoutError)
        async def test_a():
            await asyncio.sleep(1)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(xfailed=1)


def test_timeout_disabled(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio(timeout=0)
        async def test_a():
            await asyncio.sleep(0.01)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_timeout_not_numeric(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio(timeout="abc")
        @pytest.mark.xfail(strict=True, raises=ValueError)
        async def test_a():
            await asyncio.sleep(0.01)
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(xfailed=1)


def test_timeout_cmdline(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio
        @pytest.mark.xfail(strict=True, raises=asyncio.TimeoutError)
        async def test_a():
            await asyncio.sleep(1)
        """
        )
    )
    result = pytester.runpytest("--asyncio-timeout=0.01", "--asyncio-mode=strict")
    result.assert_outcomes(xfailed=1)


def test_timeout_cfg(pytester):
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = 'pytest_asyncio'

        @pytest.mark.asyncio
        @pytest.mark.xfail(strict=True, raises=asyncio.TimeoutError)
        async def test_a():
            await asyncio.sleep(1)
        """
        )
    )
    pytester.makefile(".ini", pytest="[pytest]\nasyncio_timeout = 0.01\n")
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(xfailed=1)
