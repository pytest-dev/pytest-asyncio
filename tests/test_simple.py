"""Quick'n'dirty unit tests for provided fixtures and markers."""

import asyncio
from textwrap import dedent

import pytest
from pytest import Pytester


async def async_coro():
    await asyncio.sleep(0)
    return "ok"


def test_event_loop_fixture(event_loop):
    """Test the injection of the event_loop fixture."""
    assert event_loop
    ret = event_loop.run_until_complete(async_coro())
    assert ret == "ok"


@pytest.mark.asyncio
async def test_asyncio_marker():
    """Test the asyncio pytest marker."""
    await asyncio.sleep(0)


def test_asyncio_marker_compatibility_with_xfail(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest_plugins = "pytest_asyncio"

                @pytest.mark.xfail(reason="need a failure", strict=True)
                @pytest.mark.asyncio
                async def test_asyncio_marker_fail():
                    raise AssertionError
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(xfailed=1)


def test_asyncio_auto_mode_compatibility_with_xfail(pytester: Pytester):
    pytester.makepyfile(
        dedent(
            """\
                import pytest

                pytest_plugins = "pytest_asyncio"

                @pytest.mark.xfail(reason="need a failure", strict=True)
                async def test_asyncio_marker_fail():
                    raise AssertionError
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(xfailed=1)


@pytest.mark.asyncio
async def test_asyncio_marker_with_default_param(a_param=None):
    """Test the asyncio pytest marker."""
    await asyncio.sleep(0)


class TestMarkerInClassBasedTests:
    """Test that asyncio marked functions work for methods of test classes."""

    @pytest.mark.asyncio
    async def test_asyncio_marker_with_implicit_loop_fixture(self):
        """Test the "asyncio" marker works on a method in
        a class-based test with implicit loop fixture."""
        ret = await async_coro()
        assert ret == "ok"


class TestEventLoopStartedBeforeFixtures:
    @pytest.fixture
    async def loop(self):
        return asyncio.get_event_loop()

    @staticmethod
    def foo():
        return 1

    @pytest.mark.asyncio
    async def test_no_event_loop(self, loop):
        assert await loop.run_in_executor(None, self.foo) == 1

    @pytest.mark.asyncio
    async def test_event_loop_after_fixture(self, loop):
        assert await loop.run_in_executor(None, self.foo) == 1

    @pytest.mark.asyncio
    async def test_event_loop_before_fixture(self, loop):
        assert await loop.run_in_executor(None, self.foo) == 1


def test_invalid_asyncio_mode(testdir):
    result = testdir.runpytest("-o", "asyncio_mode=True")
    result.stderr.no_fnmatch_line("INTERNALERROR> *")
    result.stderr.fnmatch_lines(
        "ERROR: 'True' is not a valid asyncio_mode. Valid modes: auto, strict."
    )
