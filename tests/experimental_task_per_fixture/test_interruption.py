"""
Ctrl-C and pytest-timeout with asyncio_experimental_task_per_fixture.

The interrupted test or fixture is cancelled, and its cleanup runs while
its fixtures are still set up. A second Ctrl-C ends the wait for that
cleanup, which then runs when the loop closes. A loop callback raising
KeyboardInterrupt stands in for Ctrl-C.
"""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio_experimental_task_per_fixture requires Python 3.11",
)


@pytest.mark.skipif(sys.platform == "win32", reason="Uses pytest-timeout's signals")
def test_pytest_timeout_lets_the_test_cleanup_use_its_fixtures(pytester: Pytester):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def report():
            with open("report.txt", "w") as stream:
                yield stream

        @pytest.mark.timeout(0.5, func_only=True)
        @pytest.mark.asyncio
        async def test_hang(report):
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                report.write("saved during cleanup")
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict",
        "-p",
        "timeout",
        "-o",
        "timeout_method=signal",
        timeout=30,
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*_ test_hang _*", "*Failed: Timeout*0.5s*"])
    assert (pytester.path / "report.txt").read_text() == "saved during cleanup"


def test_a_test_calling_sys_exit_fails_and_later_tests_use_its_loop(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import sys

        import pytest

        @pytest.mark.asyncio(loop_scope="module")
        async def test_exits():
            sys.exit(3)

        @pytest.mark.asyncio(loop_scope="module")
        async def test_next():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1, passed=1)
    result.stdout.fnmatch_lines(["*_ test_exits _*", "*SystemExit: 3"])
    assert "pytest-asyncio received" not in result.stdout.str()


def test_a_cleanup_error_after_ctrl_c_fails_the_test_and_the_session_continues(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest.mark.asyncio(loop_scope="module")
        async def test_interrupted():
            asyncio.get_running_loop().call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
            finally:
                raise ValueError("cleanup failed")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_next():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.assert_outcomes(failed=1, passed=1)
    result.stdout.fnmatch_lines(
        ["*_ test_interrupted _*", "*ValueError: cleanup failed", "*KeyboardInterrupt*"]
    )


def test_sys_exit_during_cleanup_after_ctrl_c_fails_the_test_and_names_the_ctrl_c(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        import sys

        import pytest

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest.mark.asyncio
        async def test_exits_during_cleanup():
            asyncio.get_running_loop().call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
            finally:
                sys.exit(3)

        def test_next():
            pass
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(failed=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*SystemExit: 3",
            "*Raised during cleanup after pytest-asyncio received: KeyboardInterrupt()",
        ]
    )
    assert "never retrieved" not in result.stdout.str() + result.stderr.str()


@pytest.mark.skipif(sys.platform == "win32", reason="Uses pytest-timeout's signals")
def test_a_cleanup_error_after_pytest_timeout_is_reported_with_the_timeout(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        @pytest.mark.timeout(0.1, func_only=True)
        @pytest.mark.asyncio
        async def test_hang():
            try:
                await asyncio.Event().wait()
            finally:
                raise ConnectionError("cleanup failed")
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict",
        "-p",
        "timeout",
        "-o",
        "timeout_method=signal",
        timeout=30,
    )

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        ["*_ test_hang _*", "*ConnectionError: cleanup failed", "*Timeout*"]
    )


def test_a_cleanup_error_in_a_fixture_setup_after_ctrl_c_is_a_setup_error(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest_asyncio.fixture
        async def resource():
            asyncio.get_running_loop().call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
                yield
            finally:
                raise ValueError("setup cleanup failed")

        @pytest.mark.asyncio
        async def test_uses_resource(resource):
            pytest.fail("the fixture setup should have failed")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_uses_resource*",
            "*ValueError: setup cleanup failed",
            "*KeyboardInterrupt*",
        ]
    )


def test_a_fixture_failing_during_the_test_cleanup_after_ctrl_c_cancels_that_cleanup(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        from pathlib import Path

        import pytest
        import pytest_asyncio

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest_asyncio.fixture
        async def service():
            failure = asyncio.Event()

            async def fail():
                await failure.wait()
                raise RuntimeError("service failed")

            async with asyncio.TaskGroup() as group:
                group.create_task(fail())
                yield failure

        @pytest.mark.asyncio
        async def test_interrupted(service):
            asyncio.get_running_loop().call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
            finally:
                service.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    Path("cleanup.txt").write_text("cancelled")
                    raise
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.stdout.fnmatch_lines(["*! KeyboardInterrupt !*"])
    assert (pytester.path / "cleanup.txt").read_text() == "cancelled"


def test_a_fixture_that_yields_as_ctrl_c_arrives_is_torn_down_before_its_parent(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest.fixture
        def output():
            with open("report.txt", "w") as stream:
                yield stream

        @pytest_asyncio.fixture
        async def report(output):
            asyncio.get_running_loop().call_soon(ctrl_c)
            yield output
            await asyncio.sleep(0)
            output.write("saved during teardown")

        @pytest.mark.asyncio
        async def test_uses_report(report):
            pytest.fail("the fixture setup should have been interrupted")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes()
    assert (pytester.path / "report.txt").read_text() == "saved during teardown"


def test_cleanup_abandoned_by_a_second_interruption_finishes_when_the_loop_closes(
    pytester: Pytester,
):
    """A stopped loop interrupts the test and its cleanup only."""
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        import gc
        from pathlib import Path

        import pytest

        @pytest.mark.asyncio(loop_scope="module")
        async def test_interrupted_twice():
            loop = asyncio.get_running_loop()
            loop.call_soon(loop.stop)
            try:
                await asyncio.Event().wait()
            finally:
                loop.call_soon(loop.stop)
                try:
                    await asyncio.Event().wait()
                finally:
                    await asyncio.sleep(0)
                    Path("cleanup.txt").write_text("finished")

        def test_collects_garbage():
            gc.collect()
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1, passed=1)
    assert (pytester.path / "cleanup.txt").read_text() == "finished"


def test_a_second_ctrl_c_after_cleanup_still_closes_async_generators(
    pytester: Pytester,
):
    """
    The second Ctrl-C is raised once every task is done, after asyncio
    has queued the callback that stops that run of the loop.
    """
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        from pathlib import Path

        import pytest

        def ctrl_c():
            raise KeyboardInterrupt

        def ctrl_c_once_every_task_is_done():
            loop = asyncio.get_running_loop()
            if asyncio.all_tasks(loop):
                loop.call_soon(ctrl_c_once_every_task_is_done)
            else:
                raise KeyboardInterrupt

        async def numbers():
            try:
                yield 1
            finally:
                Path("generator.txt").write_text("closed")

        unfinished_generators = []

        @pytest.mark.asyncio
        async def test_interrupted():
            unfinished_generators.append(numbers())
            await anext(unfinished_generators[0])
            loop = asyncio.get_running_loop()
            loop.call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
            finally:
                loop.call_soon(ctrl_c_once_every_task_is_done)
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert (pytester.path / "generator.txt").read_text() == "closed"
