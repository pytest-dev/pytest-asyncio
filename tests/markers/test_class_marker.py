"""Test if pytestmark works when defined on a class."""
import asyncio
from textwrap import dedent

import pytest


class TestPyTestMark:
    pytestmark = pytest.mark.asyncio

    async def test_is_asyncio(self, event_loop, sample_fixture):
        assert asyncio.get_event_loop()
        counter = 1

        async def inc():
            nonlocal counter
            counter += 1
            await asyncio.sleep(0)

        await asyncio.ensure_future(inc())
        assert counter == 2


@pytest.fixture
def sample_fixture():
    return None


def test_asyncio_event_loop_mark_provides_class_scoped_loop_strict_mode(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio_event_loop
            class TestClassScopedLoop:
                loop: asyncio.AbstractEventLoop

                @pytest.mark.asyncio
                async def test_remember_loop(self):
                    TestClassScopedLoop.loop = asyncio.get_running_loop()

                @pytest.mark.asyncio
                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is TestClassScopedLoop.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_asyncio_event_loop_mark_provides_class_scoped_loop_auto_mode(
    pytester: pytest.Pytester,
):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio_event_loop
            class TestClassScopedLoop:
                loop: asyncio.AbstractEventLoop

                async def test_remember_loop(self):
                    TestClassScopedLoop.loop = asyncio.get_running_loop()

                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is TestClassScopedLoop.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=2)


def test_asyncio_event_loop_mark_is_inherited_to_subclasses(pytester: pytest.Pytester):
    pytester.makepyfile(
        dedent(
            """\
            import asyncio
            import pytest

            @pytest.mark.asyncio_event_loop
            class TestSuperClassWithMark:
                pass

            class TestWithoutMark(TestSuperClassWithMark):
                loop: asyncio.AbstractEventLoop

                @pytest.mark.asyncio
                async def test_remember_loop(self):
                    TestWithoutMark.loop = asyncio.get_running_loop()

                @pytest.mark.asyncio
                async def test_this_runs_in_same_loop(self):
                    assert asyncio.get_running_loop() is TestWithoutMark.loop
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
