"""
The event loop of a scope stays current until it has closed, and it is
closed however the scope ends.

Tests that check whether a loop closed record it from
pytest_unconfigure.
"""

from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_a_custom_loop_remains_current_while_it_closes(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class Loop(asyncio.SelectorEventLoop):
            def close(self):
                if not self.is_closed():
                    assert asyncio.get_event_loop() is self
                super().close()

        def pytest_asyncio_loop_factories(config, item):
            return {"custom": Loop}
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        @pytest.mark.asyncio
        async def test_uses_the_loop():
            pass
        """))

    result = pytester.runpytest("--asyncio-mode=strict", "-W", "error")

    result.assert_outcomes(passed=1)


def test_a_loop_that_refuses_every_task_fails_its_tests_and_is_closed(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = module")
    pytester.makeconftest(dedent("""\
        import asyncio
        from pathlib import Path

        loops = []

        def reject_task(loop, coro, **kwargs):
            coro.close()
            raise RuntimeError("no tasks on this loop")

        def loop_factory():
            loop = asyncio.new_event_loop()
            loop.set_task_factory(reject_task)
            loops.append(loop)
            return loop

        def pytest_asyncio_loop_factories(config, item):
            return {"refusing": loop_factory}

        def pytest_unconfigure(config):
            closed = [loop.is_closed() for loop in loops]
            Path("loops-closed.txt").write_text(str(closed))
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        @pytest.mark.asyncio(loop_scope="module")
        async def test_first():
            pass

        @pytest.mark.asyncio(loop_scope="module")
        async def test_second():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(["*RuntimeError: no tasks on this loop*"])
    assert (pytester.path / "loops-closed.txt").read_text() == "[True]"


def test_ctrl_c_before_the_first_async_test_still_closes_the_loop(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio
        from pathlib import Path

        loops = []

        def ctrl_c():
            raise KeyboardInterrupt

        def loop_factory():
            loop = asyncio.new_event_loop()
            loop.call_soon(ctrl_c)
            loops.append(loop)
            return loop

        def pytest_asyncio_loop_factories(config, item):
            return {"interrupted": loop_factory}

        def pytest_unconfigure(config):
            closed = [loop.is_closed() for loop in loops]
            Path("loops-closed.txt").write_text(str(closed))
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        @pytest.mark.asyncio
        async def test_interrupted():
            pytest.fail("Ctrl-C should have stopped the session")
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    assert result.ret == pytest.ExitCode.INTERRUPTED
    assert (pytester.path / "loops-closed.txt").read_text() == "[True]"
    output = result.stdout.str() + result.stderr.str()
    for noise in ("Task was destroyed", "never awaited", "never retrieved"):
        assert noise not in output


def test_ctrl_c_while_the_loop_closes_still_closes_it(pytester: Pytester):
    """
    Pytest does not handle a KeyboardInterrupt raised as its session
    finishes, so the process ends as it does for any uncaught
    KeyboardInterrupt.
    """
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio
        from pathlib import Path

        loops = []

        def loop_factory():
            loop = asyncio.new_event_loop()
            loops.append(loop)
            return loop

        def pytest_asyncio_loop_factories(config, item):
            return {"tracked": loop_factory}

        def pytest_unconfigure(config):
            closed = [loop.is_closed() for loop in loops]
            Path("loops-closed.txt").write_text(str(closed))
        """))
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        def ctrl_c():
            raise KeyboardInterrupt("while the loop closes")

        @pytest.mark.asyncio
        async def test_interrupted(request):
            loop = asyncio.get_running_loop()
            request.addfinalizer(lambda: loop.call_soon(ctrl_c))
            raise KeyboardInterrupt
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    output = result.stdout.str() + result.stderr.str()
    assert "KeyboardInterrupt: while the loop closes" in output
    assert (pytester.path / "loops-closed.txt").read_text() == "[True]"


def test_a_loop_factory_error_is_a_setup_error_of_every_test_on_the_loop(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = module")
    pytester.makeconftest(dedent("""\
        def unavailable_loop():
            with open("factory-calls.txt", "a") as calls:
                calls.write("called\\n")
            raise LookupError("the loop is unavailable")

        def pytest_asyncio_loop_factories(config, item):
            return {"unavailable": unavailable_loop}
        """))
    pytester.makepyfile(dedent("""\
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="module", loop_scope="module")
        async def value():
            return 42

        @pytest.mark.asyncio(loop_scope="module")
        async def test_first(value):
            pass

        @pytest.mark.asyncio(loop_scope="module")
        async def test_second(value):
            pass
        """))

    result = pytester.runpytest("--asyncio-mode=strict")

    result.assert_outcomes(errors=2)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_first*",
            "*LookupError: the loop is unavailable*",
            "*ERROR at setup of test_second*",
            "*LookupError: the loop is unavailable*",
        ]
    )
    assert (pytester.path / "factory-calls.txt").read_text() == "called\n"


def test_a_sync_test_closing_the_shared_loop_fails_later_async_tests(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        @pytest.mark.asyncio(loop_scope="module")
        async def test_first():
            pass

        def test_closes_the_loop():
            asyncio.get_event_loop().close()

        @pytest.mark.asyncio(loop_scope="module")
        async def test_after_close():
            pass
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "default", timeout=30
    )

    result.assert_outcomes(passed=2, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*_ test_after_close _*",
            "*RuntimeError: Event loop is closed*",
            "*RuntimeWarning:*closed the underlying event loop*",
        ]
    )


def test_a_sync_test_closing_the_loop_of_an_async_fixture_fails_its_teardown(
    pytester: Pytester,
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest_asyncio

        @pytest_asyncio.fixture
        async def resource():
            yield

        def test_closes_the_loop(resource):
            asyncio.get_event_loop().close()
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "default", timeout=30
    )

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*_ ERROR at teardown of test_closes_the_loop _*",
            "E * RuntimeError: Event loop is closed",
            "*RuntimeWarning:*closed the underlying event loop*",
        ]
    )
    result.stdout.no_fnmatch_line("*ExceptionGroup*")
