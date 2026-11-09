from __future__ import annotations

import pytest
from pytest import Pytester


@pytest.mark.parametrize("mode", ["auto", "strict"])
@pytest.mark.parametrize("scope", ["function", "module"])
def test_callback_warning(pytester: Pytester, mode: str, scope: str):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(f"""
        import asyncio
        import pytest

        @pytest.mark.asyncio(loop_scope={scope!r})
        async def test_callback():
            def fail():
                raise ValueError("callback failed")
            loop = asyncio.get_running_loop()
            loop.call_soon(fail)
            await asyncio.sleep(0)

        @pytest.mark.asyncio(loop_scope={scope!r})
        async def test_clean():
            await asyncio.sleep(0)
    """)
    result = pytester.runpytest(
        f"--asyncio-mode={mode}",
        "-W",
        "default::pytest_asyncio.PytestAsyncioUnhandledExceptionWarning",
    )
    result.assert_outcomes(passed=2, warnings=1)
    result.stdout.fnmatch_lines(
        ["*PytestAsyncioUnhandledExceptionWarning*", "*ValueError: callback failed*"]
    )
    result.stderr.no_fnmatch_line("*Exception in callback*")


@pytest.mark.parametrize("count", [1, 2])
def test_warning_as_error(pytester: Pytester, count: int):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(f"""
        import asyncio
        import pytest

        @pytest.mark.asyncio
        async def test_unhandled():
            loop = asyncio.get_running_loop()
            for _ in range({count}):
                loop.call_exception_handler({{
                    "message": "unhandled callback",
                    "exception": ValueError("bad callback"),
                }})

        @pytest.mark.asyncio
        async def test_clean():
            await asyncio.sleep(0)
    """)
    result = pytester.runpytest(
        "-W", "error::pytest_asyncio.PytestAsyncioUnhandledExceptionWarning"
    )
    result.assert_outcomes(failed=1, passed=1)
    result.stdout.fnmatch_lines(["*PytestAsyncioUnhandledExceptionWarning*"])
    result.stderr.no_fnmatch_line("*Unhandled error in exception handler*")


def test_custom_handler_and_handled_errors(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile("""
        import asyncio
        import pytest

        @pytest.mark.asyncio
        async def test_custom_handler():
            loop = asyncio.get_running_loop()
            old_handler = loop.get_exception_handler()
            seen = []
            loop.set_exception_handler(lambda loop, context: seen.append(context))
            try:
                loop.call_exception_handler({"message": "custom event"})
                assert len(seen) == 1
            finally:
                loop.set_exception_handler(old_handler)

        @pytest.mark.asyncio
        async def test_handled_error_and_cancellation():
            async def fail():
                raise ValueError("handled")
            with pytest.raises(ValueError):
                await asyncio.create_task(fail())
            task = asyncio.create_task(asyncio.sleep(100))
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    """)
    result = pytester.runpytest("-Werror")
    result.assert_outcomes(passed=2)


def test_fixture_setup_and_teardown_warnings(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile("""
        import asyncio
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def resource():
            loop = asyncio.get_running_loop()
            loop.call_exception_handler({"message": "setup context without exception"})
            yield
            loop.call_exception_handler({
                "message": "teardown context without exception"
            })

        async def test_resource(resource):
            pass
    """)
    result = pytester.runpytest(
        "--asyncio-mode=auto",
        "-W",
        "default::pytest_asyncio.PytestAsyncioUnhandledExceptionWarning",
    )
    result.assert_outcomes(passed=1, warnings=2)
    result.stdout.fnmatch_lines(
        ["*setup context without exception*", "*teardown context without exception*"]
    )


def test_factory_handler_preserved(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest("""
        import asyncio

        def custom_handler(loop, context):
            assert context["message"] == "custom event"

        def factory():
            loop = asyncio.new_event_loop()
            loop.set_exception_handler(custom_handler)
            return loop

        def pytest_asyncio_loop_factories():
            return {"custom": factory}
    """)
    pytester.makepyfile("""
        import asyncio
        import conftest
        import pytest

        @pytest.mark.asyncio
        async def test_handler():
            loop = asyncio.get_running_loop()
            assert loop.get_exception_handler() is conftest.custom_handler
            loop.call_exception_handler({"message": "custom event"})
    """)
    result = pytester.runpytest("-Werror")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("filter_action", ["default", "error"])
def test_teardown_error_does_not_leak_warning(pytester: Pytester, filter_action: str):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile("""
        import asyncio
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def resource():
            yield
            asyncio.get_running_loop().call_exception_handler({
                "message": "unhandled teardown event"
            })
            raise ValueError("fixture teardown failed")

        async def test_resource(resource):
            pass

        async def test_clean():
            pass
    """)
    result = pytester.runpytest(
        "--asyncio-mode=auto",
        "-W",
        f"{filter_action}::pytest_asyncio.PytestAsyncioUnhandledExceptionWarning",
    )
    result.assert_outcomes(passed=2, errors=1, warnings=int(filter_action == "default"))
    result.stdout.fnmatch_lines(["*fixture teardown failed*"])
    result.stdout.fnmatch_lines(["*unhandled teardown event*"])


def test_warning_ignored_and_cancelled_context(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile("""
        import asyncio
        import pytest

        @pytest.mark.asyncio
        @pytest.mark.filterwarnings("ignore::pytest_asyncio.PytestAsyncioUnhandledExceptionWarning")
        async def test_ignored():
            asyncio.get_running_loop().call_exception_handler({
                "message": "ignored event"
            })

        @pytest.mark.asyncio
        async def test_cancelled_context():
            asyncio.get_running_loop().call_exception_handler({
                "exception": asyncio.CancelledError()
            })
    """)
    result = pytester.runpytest("-Werror")
    result.assert_outcomes(passed=2)


def test_handler_restored_after_runner_close(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest("""
        import asyncio

        loops = []

        def factory():
            loop = asyncio.new_event_loop()
            loops.append(loop)
            return loop

        def pytest_asyncio_loop_factories():
            return {"owned": factory}

        def pytest_sessionfinish():
            assert loops
            assert all(loop.is_closed() for loop in loops)
            assert all(loop.get_exception_handler() is None for loop in loops)
    """)
    pytester.makepyfile("""
        import pytest

        @pytest.mark.asyncio
        async def test_loop():
            pass
    """)
    result = pytester.runpytest("-Werror")
    result.assert_outcomes(passed=1)
