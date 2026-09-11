"""
Ctrl-C and pytest-timeout while async tests and fixtures run.

Tests that send SIGINT run on POSIX only. Where the signal itself does
not matter, a loop callback raising KeyboardInterrupt stands in for
Ctrl-C.
"""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.skipif(sys.platform == "win32", reason="Sends SIGINT with os.kill")
def test_ctrl_c_lets_the_test_cleanup_use_its_fixtures(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        import os
        import signal

        import pytest
        import pytest_asyncio

        # asyncio.Runner handles SIGINT only if the default handler is
        # installed. The process that runs pytest may ignore SIGINT.
        signal.signal(signal.SIGINT, signal.default_int_handler)

        @pytest_asyncio.fixture
        async def report():
            with open("report.txt", "w") as stream:
                yield stream

        @pytest.mark.asyncio
        async def test_interrupted(report):
            asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGINT)
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                report.write("saved during cleanup")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert (pytester.path / "report.txt").read_text() == "saved during cleanup"


@pytest.mark.skipif(sys.platform == "win32", reason="Sends SIGINT with os.kill")
def test_ctrl_c_cancels_the_test_once(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        import os
        import signal
        from pathlib import Path

        import pytest

        # asyncio.Runner handles SIGINT only if the default handler is
        # installed. The process that runs pytest may ignore SIGINT.
        signal.signal(signal.SIGINT, signal.default_int_handler)

        @pytest.mark.asyncio
        async def test_interrupted():
            asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGINT)
            try:
                await asyncio.Event().wait()
            finally:
                cancelling = asyncio.current_task().cancelling()
                Path("cancelling.txt").write_text(str(cancelling))
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert (pytester.path / "cancelling.txt").read_text() == "1"


def test_ctrl_c_stops_the_session_even_if_the_test_suppresses_the_cancellation(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        from pathlib import Path

        import pytest

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest.mark.asyncio
        async def test_interrupted():
            asyncio.get_running_loop().call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
            Path("finished.txt").write_text("ran to its end")

        @pytest.mark.asyncio
        async def test_next():
            pytest.fail("the session should have stopped")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes()
    assert (pytester.path / "finished.txt").read_text() == "ran to its end"


@pytest.mark.skipif(sys.platform == "win32", reason="Sends SIGINT with os.kill")
def test_ctrl_c_during_an_async_fixture_teardown_cancels_it_where_it_waits(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        import os
        import signal
        from pathlib import Path

        import pytest
        import pytest_asyncio

        # asyncio.Runner handles SIGINT only if the default handler is
        # installed. The process that runs pytest may ignore SIGINT.
        signal.signal(signal.SIGINT, signal.default_int_handler)

        @pytest_asyncio.fixture
        async def resource():
            yield
            asyncio.get_running_loop().call_soon(os.kill, os.getpid(), signal.SIGINT)
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                Path("teardown.txt").write_text("cancelled while waiting")
                raise

        @pytest.mark.asyncio
        async def test_uses_resource(resource):
            pass
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes(passed=1)
    assert (pytester.path / "teardown.txt").read_text() == "cancelled while waiting"
    assert "Task was destroyed" not in result.stdout.str() + result.stderr.str()


def test_ctrl_c_stops_the_session_when_the_test_cleanup_cancels_every_other_task(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        def ctrl_c():
            raise KeyboardInterrupt

        @pytest.mark.asyncio
        async def test_interrupted():
            asyncio.get_running_loop().call_soon(ctrl_c)
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                current = asyncio.current_task()
                others = [task for task in asyncio.all_tasks() if task is not current]
                for task in others:
                    task.cancel()
                await asyncio.gather(*others, return_exceptions=True)

        @pytest.mark.asyncio
        async def test_next():
            pytest.fail("the session should have stopped")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes()


def test_ctrl_c_just_after_a_test_finishes_stops_the_session(pytester: Pytester):
    """
    A Ctrl-C that arrives after the test's last task finishes, but
    before its loop stops, is not lost.

    The callback raises once no task is left. That is after asyncio has
    queued the callback that stops this run of the loop, provided
    pytest-asyncio keeps no task of its own alive after the test.
    """
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        def ctrl_c_once_every_task_is_done():
            loop = asyncio.get_running_loop()
            if asyncio.all_tasks(loop):
                loop.call_soon(ctrl_c_once_every_task_is_done)
            else:
                raise KeyboardInterrupt

        @pytest.mark.asyncio
        async def test_finishes():
            asyncio.get_running_loop().call_soon(ctrl_c_once_every_task_is_done)

        @pytest.mark.asyncio
        async def test_next():
            pytest.fail("the session should have stopped")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.stdout.fnmatch_lines(["*! KeyboardInterrupt !*"])
    result.assert_outcomes()


def test_ctrl_c_is_reported_when_the_interrupted_fixture_setup_returns_without_yielding(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
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
            except asyncio.CancelledError:
                return
            yield

        @pytest.mark.asyncio
        async def test_uses_resource(resource):
            pytest.fail("the fixture setup should have been interrupted")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    assert result.ret == pytest.ExitCode.INTERRUPTED
    result.assert_outcomes()
    assert "StopAsyncIteration" not in result.stdout.str()


@pytest.mark.skipif(sys.platform == "win32", reason="Uses pytest-timeout's signals")
def test_pytest_timeout_fails_a_test_hung_in_a_busy_loop(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import pytest

        @pytest.mark.timeout(0.5, func_only=True)
        @pytest.mark.asyncio
        async def test_hang():
            while True:
                pass
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
