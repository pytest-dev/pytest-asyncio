"""Setup, yield and teardown errors of async generator fixtures."""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester


def test_a_failing_test_leaves_its_fixture_to_run_its_cleanup_after_the_yield(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        cleanup = []

        @pytest_asyncio.fixture
        async def resource():
            yield
            await asyncio.sleep(0)
            cleanup.append("ran after the yield")

        @pytest.mark.asyncio
        async def test_fails(resource):
            raise AssertionError("reported to pytest")

        def test_cleanup_ran():
            assert cleanup == ["ran after the yield"]
        """))

    result = pytester.runpytest("--asyncio-mode=strict")

    result.assert_outcomes(failed=1, passed=1)
    result.stdout.fnmatch_lines(["*AssertionError: reported to pytest*"])


def test_a_fixture_that_never_yields_is_a_setup_error(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def generator():
            return
            yield

        @pytest.mark.asyncio
        async def test_uses_generator(generator):
            pass
        """))

    result = pytester.runpytest("--asyncio-mode=strict")

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*ERROR at setup of test_uses_generator*"])


def test_a_fixture_that_yields_twice_is_a_teardown_error(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def generator():
            yield
            yield

        @pytest.mark.asyncio
        async def test_uses_generator(generator):
            pass
        """))

    result = pytester.runpytest("--asyncio-mode=strict")

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_uses_generator*",
            "*ValueError: Async generator fixture*didn't stop*",
        ]
    )


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="asyncio.TaskGroup requires Python 3.11"
)
def test_a_task_group_child_failing_during_fixture_setup_is_a_setup_error(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = module")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            async def fail():
                raise RuntimeError("background service failed")

            async with asyncio.TaskGroup() as group:
                group.create_task(fail())
                await asyncio.Event().wait()
                yield

        @pytest.mark.asyncio(loop_scope="module")
        async def test_uses_service(service):
            pass

        @pytest.mark.asyncio(loop_scope="module")
        async def test_next():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_uses_service*",
            "*RuntimeError: background service failed*",
        ]
    )
